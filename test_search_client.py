#!/usr/bin/env python3

import asyncio
import httpx
from uuid import uuid4
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest


async def test_paper_search_agent():
    base_url = "http://localhost:10000"

    async with httpx.AsyncClient() as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )

        try:
            # Fetch agent card
            print(f"Fetching agent card from: {base_url}")
            agent_card = await resolver.get_agent_card()
            print(f"Successfully fetched agent card: {agent_card.name}")

            # Initialize client
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

            # Send test message
            send_message_payload = {
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": "Find papers about transformer attention mechanisms",
                        }
                    ],
                    "messageId": uuid4().hex,
                },
            }

            request = SendMessageRequest(
                id=str(uuid4()), params=MessageSendParams(**send_message_payload)
            )

            print(
                "Sending search query: 'Find papers about transformer attention mechanisms'"
            )
            response = await client.send_message(request)
            print("Response received:")
            print(response.model_dump(mode="json", exclude_none=True))

        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_paper_search_agent())
