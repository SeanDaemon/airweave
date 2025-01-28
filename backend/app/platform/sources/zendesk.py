"""Zendesk source implementation (read-only).

Retrieves data from a user's Zendesk account, focusing on:
 - Organizations
 - Users
 - Tickets
 - Comments

and yields them as chunks using the corresponding Zendesk chunk schemas
(e.g. ZendeskOrganizationChunk, ZendeskUserChunk, ZendeskTicketChunk,
and ZendeskCommentChunk).

References:
  https://developer.zendesk.com/api-reference/ticketing/introduction/
  https://developer.zendesk.com/api-reference/ticketing/organizations/organizations/
  https://developer.zendesk.com/api-reference/ticketing/users/users/
  https://developer.zendesk.com/api-reference/ticketing/tickets/tickets/
  https://developer.zendesk.com/api-reference/ticketing/tickets/ticket_comments/
"""

from typing import AsyncGenerator, Dict, Optional

import httpx

from app.platform.auth.schemas import AuthType
from app.platform.chunks._base import BaseChunk
from app.platform.chunks.zendesk import (
    ZendeskOrganizationChunk,
    ZendeskUserChunk,
    ZendeskTicketChunk,
    ZendeskCommentChunk,
)
from app.platform.decorators import source
from app.platform.sources._base import BaseSource


@source("Zendesk", "zendesk", AuthType.oauth2_with_refresh)
class ZendeskSource(BaseSource):
    """
    Zendesk source implementation (read-only).

    Retrieves data from Zendesk for the following objects:
      - Organizations
      - Users
      - Tickets
      - Comments

    Yields them as the corresponding chunk objects defined in
    app.platform.chunks.zendesk.
    """

    @classmethod
    async def create(cls, access_token: str) -> "ZendeskSource":
        """Create a new Zendesk source instance."""
        instance = cls()
        instance.access_token = access_token
        return instance

    async def _get_with_auth(self, client: httpx.AsyncClient, url: str) -> Dict:
        """
        Make an authenticated GET request to the Zendesk API
        and return the JSON response as a dict.
        """
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    async def _generate_organization_chunks(
        self, client: httpx.AsyncClient
    ) -> AsyncGenerator[BaseChunk, None]:
        """
        Generate ZendeskOrganizationChunk objects for each organization in Zendesk.

        GET /api/v2/organizations
        """
        url = "https://your_subdomain.zendesk.com/api/v2/organizations.json"
        while url:
            data = await self._get_with_auth(client, url)
            for org in data.get("organizations", []):
                yield ZendeskOrganizationChunk(
                    source_name="zendesk",
                    entity_id=str(org["id"]),
                    name=org.get("name"),
                    domain_names=org.get("domain_names", []),
                    created_at=org.get("created_at"),
                    updated_at=org.get("updated_at"),
                    details=org.get("details"),
                    notes=org.get("notes"),
                    group_id=org.get("group_id"),
                    shared_tickets=org.get("shared_tickets", False),
                    shared_comments=org.get("shared_comments", False),
                    external_id=org.get("external_id"),
                    archived=False,  # Placeholder if needed
                )

            # Handle pagination
            url = data.get("next_page")

    async def _generate_user_chunks(
        self, client: httpx.AsyncClient
    ) -> AsyncGenerator[BaseChunk, None]:
        """
        Generate ZendeskUserChunk objects for each user in Zendesk.

        GET /api/v2/users
        """
        url = "https://your_subdomain.zendesk.com/api/v2/users.json"
        while url:
            data = await self._get_with_auth(client, url)
            for user in data.get("users", []):
                yield ZendeskUserChunk(
                    source_name="zendesk",
                    entity_id=str(user["id"]),
                    name=user.get("name"),
                    email=user.get("email"),
                    role=user.get("role"),
                    time_zone=user.get("time_zone"),
                    locale=user.get("locale"),
                    created_at=user.get("created_at"),
                    updated_at=user.get("updated_at"),
                    suspended=user.get("suspended", False),
                    archived=False,  # Placeholder if needed
                )

            # Handle pagination
            url = data.get("next_page")

    async def _generate_ticket_chunks(
        self, client: httpx.AsyncClient
    ) -> AsyncGenerator[BaseChunk, None]:
        """
        Generate ZendeskTicketChunk objects for each ticket in Zendesk.

        GET /api/v2/tickets
        """
        url = "https://your_subdomain.zendesk.com/api/v2/tickets.json"
        while url:
            data = await self._get_with_auth(client, url)
            for ticket in data.get("tickets", []):
                yield ZendeskTicketChunk(
                    source_name="zendesk",
                    entity_id=str(ticket["id"]),
                    subject=ticket.get("subject"),
                    description=ticket.get("description"),
                    type=ticket.get("type"),
                    priority=ticket.get("priority"),
                    status=ticket.get("status"),
                    tags=ticket.get("tags", []),
                    requester_id=str(ticket.get("requester_id", "")) or None,
                    assignee_id=str(ticket.get("assignee_id", "")) or None,
                    organization_id=str(ticket.get("organization_id", "")) or None,
                    group_id=str(ticket.get("group_id", "")) or None,
                    created_at=ticket.get("created_at"),
                    updated_at=ticket.get("updated_at"),
                    due_at=ticket.get("due_at"),
                    via=ticket.get("via"),
                    custom_fields=ticket.get("custom_fields", []),
                    archived=False,  # Placeholder if needed
                )
            # Handle pagination
            url = data.get("next_page")

    async def _generate_comment_chunks(
        self, client: httpx.AsyncClient, ticket_id: str
    ) -> AsyncGenerator[BaseChunk, None]:
        """
        Generate ZendeskCommentChunk objects for comments on a given ticket.

        GET /api/v2/tickets/{ticket_id}/comments
        """
        # Some Zendesk accounts use /api/v2/tickets/{ticket_id}/comments.json
        url = f"https://your_subdomain.zendesk.com/api/v2/tickets/{ticket_id}/comments.json"
        while url:
            data = await self._get_with_auth(client, url)
            for comment in data.get("comments", []):
                yield ZendeskCommentChunk(
                    source_name="zendesk",
                    entity_id=str(comment["id"]),
                    ticket_id=str(ticket_id),
                    author_id=str(comment.get("author_id", "")) or None,
                    plain_body=comment.get("plain_body"),
                    html_body=comment.get("html_body"),
                    public=comment.get("public", False),
                    created_at=comment.get("created_at"),
                    attachments=comment.get("attachments", []),
                    archived=False,  # Placeholder if needed
                )
            url = data.get("next_page")

    async def generate_chunks(self) -> AsyncGenerator[BaseChunk, None]:
        """
        Generate and yield chunks for Zendesk objects in the following order:
          - Organizations
          - Users
          - Tickets
            - Comments for each ticket
        """
        async with httpx.AsyncClient() as client:
            # 1) Yield organization chunks
            async for org_chunk in self._generate_organization_chunks(client):
                yield org_chunk

            # 2) Yield user chunks
            async for user_chunk in self._generate_user_chunks(client):
                yield user_chunk

            # 3) Yield ticket chunks, then fetch comments for each ticket
            async for ticket_chunk in self._generate_ticket_chunks(client):
                yield ticket_chunk

                # Generate comment chunks for this ticket
                async for comment_chunk in self._generate_comment_chunks(
                    client, ticket_chunk.entity_id
                ):
                    yield comment_chunk
