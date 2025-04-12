# -*- coding: utf-8 -*-
"""
pymochi - A simple Python wrapper for the Mochi.cards API.

Allows interaction with Mochi decks and cards using your API key.
"""
import requests
import json # Used only in MochiAPIError for better response formatting
from typing import Dict, List, Union, Optional, Tuple

# --- Forward Declarations ---
class MochiAPI:
    pass

# --- Deck Representation ---
class Deck:
    """
    Represents a single deck in Mochi.

    Holds the deck's ID, name, and parent ID, and provides methods
    to interact specifically with this deck (like adding cards or getting children).
    You typically get Deck objects from the MochiAPI instance (e.g., using `api.get_deck()`).

    :param api: The MochiAPI instance this deck belongs to.
    :param deck_id: The unique ID of the deck.
    :param name: The current name of the deck.
    :param parent_id: The ID of the parent deck, or None if it's top-level.
    """
    def __init__(self, api: 'MochiAPI', deck_id: str, name: str, parent_id: Optional[str] = None):
        self.api = api
        self.id = deck_id
        self.name = name
        self.parent_id = parent_id

    def add_card(self, front: str, back: str) -> Dict:
        """
        Adds a new card to *this* specific deck.

        Formats the front and back content into Mochi's Markdown style.

        :param front: The front content of the card (e.g., "What is the capital of France?").
        :param back: The back content of the card (e.g., "Paris").
        :return: A dictionary with the created card's data from the Mochi API.
        :raises: MochiAPIError on API failure.
        :Example:
            paris_card = my_deck.add_card("Capital of France?", "Paris")
            print(f"Created card ID: {paris_card.get('id')}")
        """
        content = f"{front}\n---\n{back}"
        # Delegate to the main API method for card creation
        return self.api.create_card(self.id, content)

    def get_cards(self, condensed: bool = True) -> List[Dict]:
        """
        Retrieves cards belonging to *this* specific deck.

        By default, returns a condensed list of {'front': ..., 'back': ...} dictionaries.
        Fetches full card data from the API and processes locally if condensed is True.

        :param condensed: If True (default), returns only {'front': ..., 'back': ...} for each card.
                          If False, returns the full, raw card data dictionaries from the API.
        :return: A list of dictionaries representing the cards.
        :raises: MochiAPIError on API failure.
        :Example:
            # Get just front/back (default)
            simple_cards = my_deck.get_cards()
            for card in simple_cards:
                print(f"Q: {card['front']} / A: {card['back']}")

            # Get all card details
            all_details = my_deck.get_cards(condensed=False)
            print(f"First card's full ID: {all_details[0].get('id')}")
        """
        try:
            # Step 1: Always fetch the FULL card data from the API via the MochiAPI instance.
            # The MochiAPI.get_cards method handles the actual API call.
            # We pass self.id to specify *this* deck and condensed=False to ensure
            # we get the full data needed for potential local processing.
            raw_cards_list: List[Dict] = self.api.get_cards(self.id, condensed=False)

            # Step 2: Check if the caller wants the default condensed format
            if condensed:
                # Process the raw list locally to extract front/back
                condensed_list: List[Dict[str, str]] = []
                for card_data in raw_cards_list:
                    content_string = card_data.get('content', '')
                    parts = content_string.split('\n---\n', 1)
                    front = parts[0].strip() if len(parts) > 0 else content_string.strip()
                    back = parts[1].strip() if len(parts) > 1 else ""
                    condensed_list.append({'front': front, 'back': back})
                return condensed_list # Return the locally processed list
            else:
                # If not condensed, return the raw list directly
                return raw_cards_list

        except MochiAPIError as e:
            raise MochiAPIError(f"Failed to get cards for deck '{self.name}' (ID: {self.id}): {e}", e.status_code, e.response_data) from e
        except Exception as e:
             raise MochiAPIError(f"An unexpected error occurred while getting cards for deck '{self.name}' (ID: {self.id}): {e}") from e

    def update_card(self, card_id: str, front: str, back: str) -> Dict:
        """
        Updates the content (front and back) of an existing card using its ID.

        Uses the POST method as required by the Mochi API for card updates.

        :param card_id: The unique ID of the card to update.
        :param front: The new front content for the card (Markdown).
        :param back: The new back content for the card (Markdown).
        :return: A dictionary containing the updated card's data from the API response.
        :raises: MochiAPIError if the API call fails.
        :Example:
            updated_info = my_deck.update_card("card_id_xyz", "New Question?", "New Answer!")
        """
        new_content = f"{front}\n---\n{back}"
        payload = {"content": new_content}
        endpoint = f"cards/{card_id}"
        try:
            # Delegate the API call to the MochiAPI instance using POST
            response_data = self.api._make_request("POST", endpoint, data=payload)
            return response_data
        except MochiAPIError as e:
            raise MochiAPIError(f"Failed to update card '{card_id}': {e}", e.status_code, e.response_data) from e
        except Exception as e:
             raise MochiAPIError(f"An unexpected error occurred while trying to update card '{card_id}': {e}") from e

    def get_children(self, names_only: bool = True) -> Union[List['Deck'], List[str]]:
        """
        Finds decks that are direct children of *this* specific deck.

        Uses the locally cached deck list managed by the MochiAPI instance.
        Call `api.refresh_decks()` first if you suspect the hierarchy might have changed.
        By default, returns only the names of the child decks.

        :param names_only: If True (default), returns only a list of child deck name strings.
                           If False, returns a list of the full child Deck objects.
        :return: A list of child deck names (str) or full Deck objects.
        :Example:
            child_names = my_deck.get_children()
            print(f"Children: {child_names}")

            child_objects = my_deck.get_children(names_only=False)
            if child_objects:
                print(f"First child deck ID: {child_objects[0].id}")
        """
        child_decks: List['Deck'] = []
        # Access the main deck cache via the api instance
        for deck_or_list in self.api.decks.values():
            items_to_check: List[Deck] = []
            if isinstance(deck_or_list, Deck):
                items_to_check.append(deck_or_list)
            elif isinstance(deck_or_list, list):
                items_to_check.extend(d for d in deck_or_list if isinstance(d, Deck))

            for deck_obj in items_to_check:
                # Check if the deck's parent_id matches this deck's id
                if deck_obj.parent_id == self.id:
                    child_decks.append(deck_obj)

        # Return names or full objects based on the flag (default is names_only=True)
        if not names_only:
            # Return the list of Deck objects
            return child_decks
        else:
            # Return the list of names (default behavior)
            return [deck.name for deck in child_decks]

    def update_deck(self, new_name: str) -> Dict:
        """
        Updates the name of *this* specific deck on the Mochi server.

        Also updates the name attribute of this Python Deck object and refreshes
        the main API deck cache for consistency. Uses POST as per Mochi docs.

        :param new_name: The desired new name for the deck.
        :return: A dictionary containing the updated deck's data from the API.
        :raises: MochiAPIError if the API call fails.
        :Example:
            updated_deck_data = my_deck.update_deck("A Better Name for My Deck")
        """
        endpoint = f"decks/{self.id}"
        payload = {"name": new_name}
        try:
            print(f"Attempting to update deck ID {self.id} name to: {new_name}")
            response_data = self.api._make_request("POST", endpoint, data=payload)
            print(f"API update successful for deck ID {self.id}.")

            # Update local object state immediately
            old_name = self.name
            self.name = new_name

            # Refresh the central cache in MochiAPI (CRITICAL for name changes)
            print(f"Deck ID {self.id} name updated from '{old_name}' to '{new_name}'. Refreshing API deck cache...")
            self.api.refresh_decks()
            print("Deck cache refreshed.")

            return response_data
        except MochiAPIError as e:
            raise MochiAPIError(f"Failed to update deck name for ID '{self.id}' to '{new_name}': {e}", e.status_code, e.response_data) from e
        except Exception as e:
             raise MochiAPIError(f"An unexpected error occurred while updating deck name for ID '{self.id}' to '{new_name}': {e}") from e

    # Method to be added within the Deck class

    def delete_card(self, card_id: str) -> None:
        """
        Deletes a specific card from Mochi using its unique ID.

        Note: This operates directly on the card ID. While called from a Deck
        instance, the card ID should be globally unique in Mochi. The card
        does not strictly *have* to be in the deck represented by this object,
        although typically you'd get the card ID from this deck first. Uses DELETE method.

        :param card_id: The unique ID of the card to delete.
        :return: None on success.
        :raises: MochiAPIError if the API call fails (e.g., card not found, auth error).
        :Example:
            # Assuming you have a card_id from get_cards()
            # my_deck.delete_card("the_card_id_to_delete")
        """
        # Construct the specific card endpoint for deletion
        endpoint = f"cards/{card_id}"

        # Use the MochiAPI instance's internal request method with DELETE
        try:
            print(f"Attempting to delete card ID: {card_id}")
            # _make_request handles 204 No Content correctly by returning {}
            self.api._make_request("DELETE", endpoint)
            print(f"Card {card_id} deleted successfully.")
            # No return needed for DELETE success
            return

        except MochiAPIError as e:
            # Add specific context to the error message
            if e.status_code == 404:
                 raise MochiAPIError(f"Failed to delete card: No card found with ID '{card_id}' (Error 404)", e.status_code, e.response_data) from e
            else:
                 raise MochiAPIError(f"Failed to delete card ID '{card_id}': {e}", e.status_code, e.response_data) from e
        except Exception as e:
             # Catch any other unexpected errors
             raise MochiAPIError(f"An unexpected error occurred while deleting card ID '{card_id}': {e}") from e

    def delete_deck(self) -> None:
        """
        Deletes *this* specific deck from Mochi via the API.

        :raises: MochiAPIError on API failure.
        :Example:
            # Assuming 'deck_to_delete' is a Deck object
            # deck_to_delete.delete()
        """
        # Delegate deletion to the main API method
        self.api.delete_deck(self.id)

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation of the Deck."""
        return f"Deck(id='{self.id}', name='{self.name}', parent_id='{self.parent_id}')"

# --- Custom Exception ---
class MochiAPIError(Exception):
    """
    Custom exception for errors related to the Mochi API.

    Includes the original message, and optionally the HTTP status code
    and response data received from the API for better debugging.
    """
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Union[Dict, List]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

    def __str__(self) -> str:
        """Formats the error message including status code and response if available."""
        base = super().__str__()
        if self.status_code:
            base += f" (Status Code: {self.status_code})"
        if self.response_data:
            try:
                # Attempt to pretty-print JSON response data
                response_str = json.dumps(self.response_data, indent=2)
            except TypeError:
                # Fallback for non-JSON-serializable data
                response_str = str(self.response_data)
            # Limit length for readability in tracebacks
            limit = 500
            if len(response_str) > limit:
                 response_str = response_str[:limit] + "..."
            base += f"\nAPI Response Snippet: {response_str}"
        return base

# --- Main API Client ---
class MochiAPI:
    """
    Client for interacting with the Mochi.cards API.

    Handles authentication, makes requests, and manages a local cache of decks.

    :param api_key: Your Mochi API key (find in Mochi Settings -> API).
    :raises: MochiAPIError on initialization failure (e.g., invalid API key, network issue).
    """
    def __init__(self, api_key: str):
        self.base_url = "https://app.mochi.cards/api/"
        if not api_key or not isinstance(api_key, str):
            raise ValueError("Mochi API key must be provided as a non-empty string.")
        # HTTP Basic Auth: API key as username, blank password
        self.auth: Tuple[str, str] = (api_key, '')
        # Load decks on initialization. Maps deck name -> Deck object or List[Deck] if names clash.
        self.decks: Dict[str, Union['Deck', List['Deck']]] = self._load_decks_internal()
        print(f"MochiAPI initialized. Found {self.count_decks()} decks.")

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Union[Dict, List]:
        """Internal helper to make authenticated requests to the Mochi API."""
        url = self.base_url.rstrip('/') + '/' + endpoint.lstrip('/')
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        response = None

        try:
            # print(f"DEBUG: Request {method} {url} Data: {data}") # Uncomment for debugging
            response = requests.request(
                method, url, auth=self.auth, json=data, headers=headers, timeout=20 # Slightly longer timeout
            )
            # print(f"DEBUG: Response Status: {response.status_code}") # Uncomment for debugging
            # print(f"DEBUG: Response Text: {response.text[:200]}...") # Uncomment for debugging

            response.raise_for_status()  # Raises HTTPError for 4xx/5xx status codes

            if response.status_code == 204 or not response.content:
                return {} # Standard success, no content response (e.g., DELETE)

            return response.json()

        except requests.exceptions.HTTPError as http_err:
            status_code = response.status_code if response else None
            response_data = None
            error_message = f"HTTP Error calling {method} {url}"
            if response is not None and 'application/json' in response.headers.get('Content-Type', ''):
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and 'errors' in response_data:
                         error_message += f": {response_data.get('errors')}"
                    elif isinstance(response_data, dict) and 'message' in response_data:
                         error_message += f": {response_data.get('message')}"
                    # Avoid adding raw HTML to the primary message if it wasn't JSON
                except ValueError: # JSONDecodeError
                     error_message += f": {response.text}" # Include non-JSON error text
            elif response is not None:
                 error_message += f": {response.text}" # Include non-JSON error text

            raise MochiAPIError(error_message, status_code=status_code, response_data=response_data or response.text if response else None) from http_err
        except requests.exceptions.Timeout as timeout_err:
            raise MochiAPIError(f"Request timed out after {response.request.timeout if response else '?'}s calling {method} {url}") from timeout_err
        except requests.exceptions.RequestException as req_err:
            raise MochiAPIError(f"Network or Request Error calling {method} {url}: {req_err}") from req_err
        except ValueError as json_err: # Catches JSONDecodeError
            response_text = response.text if response else "No response body"
            raise MochiAPIError(f"Failed to parse JSON response from {method} {url}. Response text: {response_text[:500]}...") from json_err

    def _load_decks_internal(self) -> Dict[str, Union['Deck', List['Deck']]]:
        """Fetches all decks from API and builds the internal cache."""
        print("Loading decks from Mochi API...")
        try:
            response_data = self._make_request("GET", "decks")
        except MochiAPIError as e:
             raise MochiAPIError(f"Failed to load decks during initialization: {e}", e.status_code, e.response_data) from e

        if isinstance(response_data, dict) and 'docs' in response_data:
            decks_list = response_data['docs']
        elif isinstance(response_data, list):
             print("Warning: Received a direct list from /decks endpoint, expected {'docs': [...]}")
             decks_list = response_data
        else:
            raise MochiAPIError(f"Unexpected format when listing decks: Expected dict with 'docs', got {type(response_data)}: {str(response_data)[:200]}...")

        if not isinstance(decks_list, list):
            raise MochiAPIError(f"Expected 'docs' field to contain a list of decks, got {type(decks_list)}")

        deck_map: Dict[str, Union['Deck', List['Deck']]] = {}
        count = 0
        for deck_data in decks_list:
            if not isinstance(deck_data, dict):
                print(f"Warning: Skipping invalid deck entry: {deck_data}")
                continue

            deck_id = deck_data.get('id') or deck_data.get('_id')
            deck_name = deck_data.get('name')
            parent_id = deck_data.get('parent-id') or deck_data.get('parent_id') or deck_data.get('parent')
            if parent_id is not None and not isinstance(parent_id, str):
                 print(f"Warning: Deck {deck_id} ('{deck_name}') has non-string parent ID '{parent_id}'. Treating as None.")
                 parent_id = None

            if not deck_id or deck_name is None: # Allow empty names "" but require an ID
                print(f"Warning: Skipping deck with missing ID or Name: {deck_data}")
                continue

            deck_obj = Deck(self, deck_id, deck_name, parent_id)
            count += 1

            if deck_name in deck_map:
                existing = deck_map[deck_name]
                if isinstance(existing, Deck):
                    deck_map[deck_name] = [existing, deck_obj]
                elif isinstance(existing, list):
                    existing.append(deck_obj)
                # else: Should not happen, ignore or log error
            else:
                deck_map[deck_name] = deck_obj
        print(f"Successfully loaded {count} decks into cache.")
        return deck_map

    def refresh_decks(self) -> None:
        """
        Reloads the deck list from the Mochi API.

        Use this if decks might have been added, deleted, or renamed outside
        of this API client instance.
        """
        print("Refreshing deck cache from Mochi API...")
        self.decks = self._load_decks_internal()

    def get_decks(self, names_only: bool = True) -> Union[List[Dict[str, str]], List[str]]:
        """
        Retrieves information about decks from the local cache.

        By default, returns only a list of unique deck names found in the cache.
        Uses the locally cached deck list. Call `refresh_decks()` first for the
        absolute latest list from the server.

        :param names_only: If True (default), returns a list of unique deck name strings.
                           If False, returns a list of dictionaries, each containing
                           {'name': 'Deck Name', 'id': 'deck_id_123'}. Handles decks
                           with duplicate names by including an entry for each one.
        :return: A list of deck names (str) or a list of deck info dictionaries.
        :Example:
            # Get just the names (default)
            deck_names = client.get_decks()
            print(deck_names)

            # Get names and IDs
            deck_details = client.get_decks(names_only=False)
            print(deck_details)
        """
        if not names_only:
            # Return list of dictionaries with name and ID
            deck_info_list: List[Dict[str, str]] = []
            for deck_or_list in self.decks.values():
                if isinstance(deck_or_list, Deck):
                    deck_info_list.append({"name": deck_or_list.name, "id": deck_or_list.id})
                elif isinstance(deck_or_list, list):
                    for deck_obj in deck_or_list:
                        if isinstance(deck_obj, Deck):
                            deck_info_list.append({"name": deck_obj.name, "id": deck_obj.id})
            return deck_info_list
        else:
            # Return only the unique names (keys of the cache)
            return list(self.decks.keys())

    def count_decks(self) -> int:
        """Counts the total number of individual decks in the cache (handles duplicates)."""
        count = 0
        for item in self.decks.values():
            if isinstance(item, list):
                count += len(item)
            else:
                count += 1
        return count

    def get_deck(self, name: str) -> Deck:
        """
        Retrieves a single Deck object by its exact name from the local cache.

        Uses the locally cached list. Call `refresh_decks()` if the deck
        might have been created recently or renamed elsewhere.

        :param name: The exact name of the deck.
        :return: The corresponding Deck object.
        :raises: ValueError if no deck is found with that name, or if multiple
                 decks share the same name (use a unique name or get by ID if needed).
        :raises: TypeError if the cache contains unexpected data for that name.
        :Example:
            spanish_deck = client.get_deck("Spanish Vocab")
            print(f"Found deck ID: {spanish_deck.id}")
        """
        if name not in self.decks:
            all_deck_names = self.get_decks(names_only=True) # Use the renamed method
            raise ValueError(
                f"No deck found with name '{name}' in local cache. "
                f"Available names: {all_deck_names}. "
                f"Try client.refresh_decks()?"
            )

        deck_or_list = self.decks[name]
        if isinstance(deck_or_list, list):
            deck_ids = [d.id for d in deck_or_list]
            raise ValueError(
                f"Multiple decks found with name '{name}'. IDs: {deck_ids}. "
                f"Cannot uniquely identify by name. Access via get_decks(names_only=False) "
                f"and filter by ID, or use a unique name."
            )
        if isinstance(deck_or_list, Deck):
            return deck_or_list
        else:
            # Should be caught by load logic or list check, but acts as safeguard
            raise TypeError(f"Internal Cache Error: Expected Deck for name '{name}', got {type(deck_or_list)}")

    def create_deck(self, name: str, parent_id: Optional[str] = None) -> Deck:
        """
        Creates a new deck in Mochi, optionally nested under a parent.

        Refreshes the local deck cache upon success to include the new deck.

        :param name: The name for the new deck.
        :param parent_id: Optional ID of the parent deck to nest this under.
        :return: A Deck object representing the newly created deck.
        :raises: MochiAPIError on API failure.
        :Example:
            # Create a top-level deck
            lang_deck = client.create_deck("Languages")

            # Create a deck nested under the first one
            french_deck = client.create_deck("French", parent_id=lang_deck.id)
        """
        payload = {"name": name}
        if parent_id:
            payload["parent-id"] = parent_id

        try:
            print(f"Attempting to create deck '{name}'...")
            created_deck_data = self._make_request("POST", "decks", payload)

            if not isinstance(created_deck_data, dict):
                raise MochiAPIError("Expected dictionary for created deck", response_data=created_deck_data)

            deck_id = created_deck_data.get('id') or created_deck_data.get('_id')
            deck_name = created_deck_data.get('name')
            deck_parent_id = created_deck_data.get('parent-id') or created_deck_data.get('parent_id') or created_deck_data.get('parent')

            if not deck_id or deck_name is None:
                raise MochiAPIError("Created deck response missing 'id' or 'name'", response_data=created_deck_data)

            print(f"Deck '{deck_name}' (ID: {deck_id}) created successfully. Refreshing cache...")
            # --- Refresh cache AFTER successful creation ---
            self.refresh_decks() # Rebuild cache to ensure new deck is loaded correctly
            print("Deck cache refreshed.")

            # --- Return the deck object from the *refreshed* cache ---
            # This ensures the returned object is the one actually in the live cache
            try:
                 # Attempt to retrieve the newly created deck from the refreshed cache
                 # This handles potential name collisions correctly based on refresh_decks logic
                 return self.get_deck(deck_name)
            except ValueError as e:
                 # If get_deck fails (e.g., due to name collision not handled as expected,
                 # or maybe API latency vs refresh), return a manually created object
                 # as a fallback, but log a warning.
                 print(f"Warning: Could not retrieve newly created deck '{deck_name}' from cache after refresh ({e}). Returning manually created object.")
                 return Deck(self, deck_id, deck_name, deck_parent_id)

        except MochiAPIError as e:
             raise MochiAPIError(f"Failed to create deck '{name}': {e}", e.status_code, e.response_data) from e
        except Exception as e:
             raise MochiAPIError(f"An unexpected error occurred while creating deck '{name}': {e}") from e

    def delete_deck(self, deck_id: str) -> None:
        """
        Deletes a deck by its ID from Mochi.

        Refreshes the local deck cache upon successful deletion.

        :param deck_id: The ID of the deck to delete.
        :raises: MochiAPIError on API failure (e.g., deck not found).
        :Example:
            # client.delete_deck("deck_id_to_remove")
        """
        try:
            print(f"Attempting to delete deck ID: {deck_id}")
            self._make_request("DELETE", f"decks/{deck_id}")
            print(f"Deck {deck_id} deleted successfully. Refreshing cache...")
            self.refresh_decks()
            print("Deck cache refreshed.")
        except MochiAPIError as e:
            # Improve error message for common "Not Found" case
            if e.status_code == 404:
                raise MochiAPIError(f"Failed to delete deck: No deck found with ID '{deck_id}' (Error 404)", e.status_code, e.response_data) from e
            else:
                raise MochiAPIError(f"Failed to delete deck ID '{deck_id}': {e}", e.status_code, e.response_data) from e
        except Exception as e:
             raise MochiAPIError(f"An unexpected error occurred while deleting deck ID '{deck_id}': {e}") from e

    ### Card Operations (on MochiAPI level)

    def create_card(self, deck_id: str, content: str) -> Dict:
        """
        Creates a new card in a specified deck (using deck ID).

        Generally, it's more convenient to use the `Deck.add_card()` method.

        :param deck_id: The ID of the target deck.
        :param content: The Markdown content (e.g., "Front\\n---\\nBack").
        :return: A dictionary containing the created card's data.
        :raises: MochiAPIError on API failure.
        """
        data = {"deck-id": deck_id, "content": content}
        try:
            return self._make_request("POST", "cards", data)
        except MochiAPIError as e:
            raise MochiAPIError(f"Failed to create card in deck ID '{deck_id}': {e}", e.status_code, e.response_data) from e
        except Exception as e:
             raise MochiAPIError(f"An unexpected error occurred creating card in deck ID '{deck_id}': {e}") from e

    def get_cards(self, deck_name_or_id: str, condensed: bool = True) -> List[Dict]:
        """
        Retrieves cards from a deck specified by its name OR ID.

        Uses the local cache to find the deck ID if a name is provided.
        By default, returns a condensed list of {'front': ..., 'back': ...}.

        :param deck_name_or_id: The name or the unique ID of the target deck.
        :param condensed: If True (default), returns only {'front': ..., 'back': ...} for each card.
                          If False, returns the full, raw card data dictionaries from the API.
        :return: A list of dictionaries representing the cards.
        :raises: ValueError if deck name/ID not found in cache or name is ambiguous.
        :raises: MochiAPIError on API failure.
        :raises: TypeError if the cache contains unexpected data types.
        :Example:
            # Get condensed cards by deck name (default)
            cards_by_name = client.get_cards("Spanish Vocab")

            # Get full card details by deck ID
            cards_by_id = client.get_cards("deck_id_xyz", condensed=False)
        """
        target_deck_id: Optional[str] = None
        ambiguous_name: bool = False
        resolved_by: Optional[str] = None

        # 1. Try finding by name first
        if deck_name_or_id in self.decks:
            deck_or_list = self.decks[deck_name_or_id]
            if isinstance(deck_or_list, list):
                ambiguous_name = True
                deck_ids = [d.id for d in deck_or_list]
            elif isinstance(deck_or_list, Deck):
                target_deck_id = deck_or_list.id
                resolved_by = "name"
            else:
                raise TypeError(f"Cache Error: Unexpected type for key '{deck_name_or_id}': {type(deck_or_list)}")

        if ambiguous_name:
             raise ValueError(f"Input '{deck_name_or_id}' matches multiple decks by name. IDs: {deck_ids}. Use a specific ID.")

        # 2. If not found by name, try finding by ID
        if target_deck_id is None:
            all_deck_objects: List[Deck] = []
            for deck_item in self.decks.values():
                 if isinstance(deck_item, Deck): all_deck_objects.append(deck_item)
                 elif isinstance(deck_item, list): all_deck_objects.extend(d for d in deck_item if isinstance(d, Deck))

            found_deck = next((deck for deck in all_deck_objects if deck.id == deck_name_or_id), None)
            if found_deck:
                target_deck_id = found_deck.id
                resolved_by = "id"

        # 3. Check if ID was found
        if target_deck_id is None:
            all_deck_names = self.get_decks(names_only=True)
            all_deck_ids = [d['id'] for d in self.get_decks(names_only=False)] # Get all IDs
            raise ValueError(
                f"No deck found with name or ID '{deck_name_or_id}' in cache. "
                f"Checked {len(all_deck_names)} names, {len(all_deck_ids)} IDs. "
                f"Try client.refresh_decks()?"
            )

        # 4. Make the API call using the resolved target_deck_id
        endpoint_with_param = f"cards?deck-id={target_deck_id}"
        try:
            response_data = self._make_request("GET", endpoint_with_param)

            # 5. Process the response and extract the raw card list
            raw_cards_list: List[Dict] = []
            if isinstance(response_data, dict) and 'docs' in response_data:
                docs_content = response_data['docs']
                if not isinstance(docs_content, list):
                     raise MochiAPIError(f"API response for cards in deck '{deck_name_or_id}' (ID: {target_deck_id}) had 'docs' but it wasn't a list.", response_data=response_data)
                raw_cards_list = docs_content
            elif isinstance(response_data, list): # Handle direct list response as fallback
                 print(f"Warning: Received direct list from {endpoint_with_param}. Assuming card list.")
                 raw_cards_list = response_data
            elif isinstance(response_data, dict) and (not response_data or response_data.get("docs") == []):
                 return [] # No cards found or empty deck is valid, return empty list
            else:
                raise MochiAPIError(f"Unexpected response format listing cards for deck '{deck_name_or_id}' (ID: {target_deck_id}). Expected dict with 'docs'.", response_data=response_data)

            # 6. Conditionally process the list for condensed output (default is condensed=True)
            if not condensed:
                # Return the full list if condensed is False
                return raw_cards_list
            else:
                # Process for condensed output (default behavior)
                condensed_list: List[Dict[str, str]] = []
                for card_data in raw_cards_list:
                    content_string = card_data.get('content', '')
                    parts = content_string.split('\n---\n', 1)
                    front = parts[0].strip() if len(parts) > 0 else content_string.strip()
                    back = parts[1].strip() if len(parts) > 1 else ""
                    condensed_list.append({'front': front, 'back': back})
                return condensed_list

        except MochiAPIError as e:
            resolution_info = f"(resolved via {resolved_by} to ID: {target_deck_id})" if resolved_by else f"(using ID: {target_deck_id})"
            raise MochiAPIError(f"Failed to get cards for deck '{deck_name_or_id}' {resolution_info}: {e}", e.status_code, e.response_data) from e
        except Exception as e:
             resolution_info = f"(resolved via {resolved_by} to ID: {target_deck_id})" if resolved_by else f"(using ID: {target_deck_id})"
             raise MochiAPIError(f"An unexpected error occurred getting cards for deck '{deck_name_or_id}' {resolution_info}: {e}") from e