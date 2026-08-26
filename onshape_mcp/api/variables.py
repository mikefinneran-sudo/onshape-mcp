"""Variable studio management for Onshape documents.

Onshape variables do not live in a Part Studio. They live in their own
VARIABLESTUDIO element, and a Part Studio sees them only once it holds a
reference to that studio. Writing a variable to a Part Studio element id is
what returns 404 - not the API version, which accepts anything from v6 up.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from .client import OnshapeClient

API = "v10"


class Variable(BaseModel):
    """A variable in an Onshape variable studio."""

    name: str
    expression: str
    description: Optional[str] = None
    type: str = "LENGTH"


class VariableStudioReference(BaseModel):
    """A Part Studio's link to a variable studio."""

    element_id: str
    entire_studio: bool = True
    variable_names: List[str] = []


class VariableManager:
    """Manager for Onshape variable studios and the references to them."""

    def __init__(self, client: OnshapeClient):
        """Initialize the variable manager.

        Args:
            client: Onshape API client
        """
        self.client = client

    async def get_variables(
        self, document_id: str, workspace_id: str, element_id: str
    ) -> List[Variable]:
        """Get the variables an element defines.

        The response is a list of blocks, each a variable studio and the
        variables it holds - not a flat list of variables. Reading a name off
        the block instead of off its variables is what returned a single blank
        row for every call.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Variable Studio element ID (a Part Studio defines no
                variables of its own and returns an empty list)

        Returns:
            List of variables
        """
        path = f"/api/{API}/variables/d/{document_id}/w/{workspace_id}/e/{element_id}/variables"
        response = await self.client.get(path)

        variables: List[Variable] = []
        for block in response or []:
            for var in block.get("variables", []) or []:
                variables.append(
                    Variable(
                        name=var.get("name", ""),
                        expression=var.get("expression", ""),
                        description=var.get("description") or None,
                        type=var.get("type", "LENGTH"),
                    )
                )
        return variables

    async def create_variable_studio(
        self, document_id: str, workspace_id: str, name: str
    ) -> Dict[str, Any]:
        """Create a variable studio element in the document.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            name: Name for the new variable studio

        Returns:
            API response, including the new element's id
        """
        path = f"/api/{API}/variables/d/{document_id}/w/{workspace_id}/variablestudio"
        return await self.client.post(path, data={"name": name})

    async def set_variable(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        name: str,
        expression: str,
        description: Optional[str] = None,
        var_type: str = "LENGTH",
    ) -> Dict[str, Any]:
        """Set or update a variable in a variable studio.

        Onshape replaces the studio's whole variable table on write, so the
        existing variables are read back and merged rather than dropped.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Variable Studio element ID
            name: Variable name
            expression: Variable expression (e.g., "0.75 in")
            description: Optional variable description
            var_type: Variable type (LENGTH, ANGLE, NUMBER, ANY)

        Returns:
            API response
        """
        return await self.set_variables(
            document_id,
            workspace_id,
            element_id,
            [Variable(name=name, expression=expression, description=description, type=var_type)],
        )

    async def set_variables(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        variables: List[Variable],
    ) -> Dict[str, Any]:
        """Set several variables in one write, merging with what is there.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Variable Studio element ID
            variables: Variables to write

        Returns:
            API response
        """
        merged: Dict[str, Variable] = {
            v.name: v for v in await self.get_variables(document_id, workspace_id, element_id)
        }
        for v in variables:
            merged[v.name] = v

        data = []
        for v in merged.values():
            entry: Dict[str, Any] = {
                "type": v.type,
                "name": v.name,
                "expression": v.expression,
            }
            if v.description:
                entry["description"] = v.description
            data.append(entry)

        path = f"/api/{API}/variables/d/{document_id}/w/{workspace_id}/e/{element_id}/variables"
        return await self.client.post(path, data=data)

    async def get_variable_studio_references(
        self, document_id: str, workspace_id: str, element_id: str
    ) -> List[VariableStudioReference]:
        """Get the variable studios an element can read.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Part Studio element ID

        Returns:
            The references the element holds
        """
        path = (
            f"/api/{API}/variables/d/{document_id}/w/{workspace_id}"
            f"/e/{element_id}/variablestudioreferences"
        )
        response = await self.client.get(path)
        return [
            VariableStudioReference(
                element_id=r.get("referenceElementId", ""),
                entire_studio=r.get("entireVariableStudio", True),
                variable_names=r.get("variableNames") or [],
            )
            for r in (response or {}).get("references", [])
        ]

    async def add_variable_studio_reference(
        self,
        document_id: str,
        workspace_id: str,
        element_id: str,
        variable_studio_id: str,
        variable_names: Optional[List[str]] = None,
    ) -> List[VariableStudioReference]:
        """Let a Part Studio read a variable studio.

        Without this the studio's variables exist but no feature in the Part
        Studio can name them. The write replaces the reference list, so the
        existing references are read back and merged.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Part Studio element ID
            variable_studio_id: Variable Studio element ID to reference
            variable_names: Optional subset of variables to expose

        Returns:
            The reference list as it stands after the write
        """
        existing = await self.get_variable_studio_references(document_id, workspace_id, element_id)
        refs = {r.element_id: r for r in existing}
        refs[variable_studio_id] = VariableStudioReference(
            element_id=variable_studio_id,
            entire_studio=not variable_names,
            variable_names=variable_names or [],
        )

        path = (
            f"/api/{API}/variables/d/{document_id}/w/{workspace_id}"
            f"/e/{element_id}/variablestudioreferences"
        )
        await self.client.post(
            path,
            data={
                "references": [
                    {
                        "referenceElementId": r.element_id,
                        "entireVariableStudio": r.entire_studio,
                        "variableNames": r.variable_names,
                    }
                    for r in refs.values()
                ]
            },
        )
        return await self.get_variable_studio_references(document_id, workspace_id, element_id)

    async def get_configuration_definition(
        self, document_id: str, workspace_id: str, element_id: str
    ) -> Dict[str, Any]:
        """Get configuration definition for an element.

        Args:
            document_id: Document ID
            workspace_id: Workspace ID
            element_id: Element ID

        Returns:
            Configuration definition
        """
        path = f"/api/{API}/elements/d/{document_id}/w/{workspace_id}/e/{element_id}/configuration"
        return await self.client.get(path)
