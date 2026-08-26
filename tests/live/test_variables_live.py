"""Round-trip the variable API against a real Onshape document.

The unit tests mock the HTTP client, so they would have passed for as long as
the variable routes returned 404 - and did. This test talks to Onshape.

It is skipped unless credentials and a target document are in the environment:

    ONSHAPE_ACCESS_KEY, ONSHAPE_SECRET_KEY
    ONSHAPE_TEST_DOCUMENT_ID, ONSHAPE_TEST_WORKSPACE_ID
    ONSHAPE_TEST_PART_STUDIO_ID          (optional, for the reference checks)

Run it with:  pytest tests/live -m live
"""

import asyncio
import os

import pytest

from onshape_mcp.api.client import OnshapeClient, OnshapeCredentials
from onshape_mcp.api.variables import VariableManager

pytestmark = pytest.mark.live

AK = os.getenv("ONSHAPE_ACCESS_KEY")
SK = os.getenv("ONSHAPE_SECRET_KEY")
DID = os.getenv("ONSHAPE_TEST_DOCUMENT_ID")
WID = os.getenv("ONSHAPE_TEST_WORKSPACE_ID")
PSID = os.getenv("ONSHAPE_TEST_PART_STUDIO_ID")

needs_live = pytest.mark.skipif(
    not (AK and SK and DID and WID),
    reason="live Onshape credentials and test document not configured",
)

STUDIO_NAME = "MCP live test variables"
PROBE = "mcp_live_probe"


async def _settle(read, want, tries=10):
    """Onshape returns 204 before the write is readable. Poll for it."""
    for _ in range(tries):
        got = await read()
        if want(got):
            return got
        await asyncio.sleep(1)
    return await read()


@pytest.fixture
async def manager():
    """A VariableManager pointed at the live API.

    Anything the test creates is torn down afterwards. These tests run
    against a real document that someone else is working in, so leaving a
    stray variable studio or a stray reference behind is not acceptable.
    """
    async with OnshapeClient(OnshapeCredentials(access_key=AK, secret_key=SK)) as client:
        vm = VariableManager(client)
        before = []
        if PSID:
            before = [r.element_id for r in await vm.get_variable_studio_references(DID, WID, PSID)]
        try:
            yield vm, client
        finally:
            if PSID:
                now = await vm.get_variable_studio_references(DID, WID, PSID)
                if [r.element_id for r in now] != before:
                    await client.post(
                        f"/api/v10/variables/d/{DID}/w/{WID}/e/{PSID}/variablestudioreferences",
                        data={
                            "references": [
                                {
                                    "referenceElementId": r.element_id,
                                    "entireVariableStudio": r.entire_studio,
                                    "variableNames": r.variable_names,
                                }
                                for r in now
                                if r.element_id in before
                            ]
                        },
                    )
            elements = await client.get(f"/api/v10/documents/d/{DID}/w/{WID}/elements")
            for el in elements:
                if el.get("elementType") == "VARIABLESTUDIO" and el.get("name", "").startswith(
                    STUDIO_NAME
                ):
                    await client.delete(f"/api/v10/elements/d/{DID}/w/{WID}/e/{el['id']}")


@needs_live
@pytest.mark.asyncio
async def test_variable_round_trip(manager):
    """Create a studio, write a variable, read the same value back."""
    vm, _ = manager
    studio = await vm.create_variable_studio(DID, WID, STUDIO_NAME)
    vsid = studio["id"]
    assert vsid

    await vm.set_variable(
        DID, WID, vsid, PROBE, "1.375 in", description="written by the live round trip"
    )
    found = await _settle(
        lambda: vm.get_variables(DID, WID, vsid),
        lambda vs: any(v.name == PROBE for v in vs),
    )
    probe = next(v for v in found if v.name == PROBE)
    assert probe.expression == "1.375 in"
    assert probe.description == "written by the live round trip"


@needs_live
@pytest.mark.asyncio
async def test_second_write_does_not_drop_the_first(manager):
    """Onshape replaces the whole table on write; the manager must merge."""
    vm, _ = manager
    vsid = (await vm.create_variable_studio(DID, WID, STUDIO_NAME + " merge"))["id"]

    await vm.set_variable(DID, WID, vsid, "first_var", "2 in")
    await _settle(
        lambda: vm.get_variables(DID, WID, vsid), lambda vs: any(v.name == "first_var" for v in vs)
    )
    await vm.set_variable(DID, WID, vsid, "second_var", "3 in")
    names = await _settle(
        lambda: vm.get_variables(DID, WID, vsid),
        lambda vs: any(v.name == "second_var" for v in vs),
    )

    assert {"first_var", "second_var"} <= {v.name for v in names}


@needs_live
@pytest.mark.asyncio
async def test_writing_to_a_part_studio_is_refused(manager):
    """The 404 that started all this. It is the element type, not the route."""
    if not PSID:
        pytest.skip("no part studio configured")
    vm, _ = manager
    import httpx

    with pytest.raises(httpx.HTTPStatusError) as err:
        await vm.set_variable(DID, WID, PSID, "should_not_exist", "1 in")
    assert err.value.response.status_code == 404


@needs_live
@pytest.mark.asyncio
async def test_part_studio_reference_survives_read_back(manager):
    """A Part Studio can name a studio's variables only once it references it."""
    if not PSID:
        pytest.skip("no part studio configured")
    vm, _ = manager
    vsid = (await vm.create_variable_studio(DID, WID, STUDIO_NAME + " ref"))["id"]

    refs = await vm.add_variable_studio_reference(DID, WID, PSID, vsid)
    assert any(r.element_id == vsid and r.entire_studio for r in refs)

    read_back = await vm.get_variable_studio_references(DID, WID, PSID)
    assert any(r.element_id == vsid for r in read_back)
