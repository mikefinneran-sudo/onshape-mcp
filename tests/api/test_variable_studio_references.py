"""Unit tests for variable studio creation and Part Studio references.

The shapes asserted here were captured from the live API against a real
document; see tests/live/test_variables_live.py for the round trip that
proves them against Onshape rather than against a mock.
"""

import pytest
from unittest.mock import AsyncMock

from onshape_mcp.api.variables import VariableManager


@pytest.fixture
def variable_manager(onshape_client):
    """Provide a VariableManager instance."""
    return VariableManager(onshape_client)


REFERENCE_RESPONSE = {
    "references": [
        {
            "referenceElementId": "96e317624f102656ebdf2940",
            "configurationIdToValue": {},
            "referenceDocumentId": "",
            "referenceVersionId": "",
            "nodeId": "MEdlOJv0lu7ADK9mu",
            "referenceId": "MEdlOJv0lu7ADK9mu",
            "variableNames": [],
            "entireVariableStudio": True,
        }
    ]
}


class TestVariableStudioCreation:
    """Creating the element variables have to live in."""

    @pytest.mark.asyncio
    async def test_create_variable_studio_posts_to_the_workspace(
        self, variable_manager, onshape_client, sample_document_ids
    ):
        """The create route is workspace level, with no element in the path."""
        onshape_client.post = AsyncMock(return_value={"id": "abc123"})

        result = await variable_manager.create_variable_studio(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            "Grader Box Variables",
        )

        assert result == {"id": "abc123"}
        path = onshape_client.post.call_args[0][0]
        assert path.endswith("/variablestudio")
        assert "/e/" not in path
        assert onshape_client.post.call_args[1]["data"] == {"name": "Grader Box Variables"}


class TestVariableStudioReferences:
    """A Part Studio can only use variables it holds a reference to."""

    @pytest.mark.asyncio
    async def test_get_references_parses_the_list(
        self, variable_manager, onshape_client, sample_document_ids
    ):
        onshape_client.get = AsyncMock(return_value=REFERENCE_RESPONSE)

        refs = await variable_manager.get_variable_studio_references(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
        )

        assert len(refs) == 1
        assert refs[0].element_id == "96e317624f102656ebdf2940"
        assert refs[0].entire_studio is True

    @pytest.mark.asyncio
    async def test_no_references_is_an_empty_list_not_an_error(
        self, variable_manager, onshape_client, sample_document_ids
    ):
        onshape_client.get = AsyncMock(return_value={"references": []})

        refs = await variable_manager.get_variable_studio_references(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
        )

        assert refs == []

    @pytest.mark.asyncio
    async def test_adding_a_reference_keeps_the_existing_ones(
        self, variable_manager, onshape_client, sample_document_ids
    ):
        """The write replaces the reference list, so it must be merged."""
        onshape_client.get = AsyncMock(return_value=REFERENCE_RESPONSE)
        onshape_client.post = AsyncMock(return_value=None)

        await variable_manager.add_variable_studio_reference(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            "ffffffffffffffffffffffff",
        )

        sent = onshape_client.post.call_args[1]["data"]["references"]
        ids = {r["referenceElementId"] for r in sent}
        assert ids == {"96e317624f102656ebdf2940", "ffffffffffffffffffffffff"}

    @pytest.mark.asyncio
    async def test_named_variables_narrow_the_reference(
        self, variable_manager, onshape_client, sample_document_ids
    ):
        onshape_client.get = AsyncMock(return_value={"references": []})
        onshape_client.post = AsyncMock(return_value=None)

        await variable_manager.add_variable_studio_reference(
            sample_document_ids["document_id"],
            sample_document_ids["workspace_id"],
            sample_document_ids["element_id"],
            "ffffffffffffffffffffffff",
            ["box_width", "plate_t"],
        )

        sent = onshape_client.post.call_args[1]["data"]["references"][0]
        assert sent["entireVariableStudio"] is False
        assert sent["variableNames"] == ["box_width", "plate_t"]
