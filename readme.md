# pymochi  Mochi API Wrapper

# convenient little python wrapper to interact with the mochi rest api

## Features

*   Connect to the Mochi API using your API key.
*   List your decks (just names or full details).
*   Get specific deck objects to work with.
*   Create new decks (top-level or nested).
*   Update deck names.
*   Find child decks.
*   Delete decks.
*   Add cards to decks.
*   List cards in a deck (just front/back or full details).
*   Update existing cards.
*   Simple error handling with custom `MochiAPIError`.



    ```python
    from pymochi import MochiAPI, MochiAPIError

    # Replace "YOUR_API_KEY_HERE" with your actual key
    api_key = "YOUR_API_KEY_HERE"

    try:
        # Create the client - this connects and loads your decks
        client = MochiAPI(api_key)
        print("Successfully connected to Mochi!")

    except MochiAPIError as e:
        print(f"Oh no! Connection failed: {e}")
    except ValueError as e:
        print(f"Error: {e}") # e.g., if API key is empty
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # --- Now you can use the 'client' object! ---
    ```

## Usage Examples

Let's assume you have a `client` object connected as shown above.

### Working with Decks

```python
# --- Listing Decks ---

# Get just the names of all your decks (default behavior)
all_deck_names = client.get_decks()
print("My deck names:", all_deck_names)
# Output: My deck names: ['Spanish Vocab', 'History Facts', 'Programming', ...]

# Get more details (name and ID for each deck)
deck_details = client.get_decks(names_only=False)
print("Deck details:", deck_details)
# Output: Deck details: [{'name': 'Spanish Vocab', 'id': 'deckId1'}, {'name': 'History Facts', 'id': 'deckId2'}, ...]

# --- Getting a Specific Deck ---

try:
    # Get a deck object by its exact name
    my_deck = client.get_deck("Spanish Vocab")
    print(f"Got deck: {my_deck.name} (ID: {my_deck.id})")

except ValueError as e:
    print(f"Couldn't find deck: {e}")

# --- Creating Decks ---

try:
    # Create a new top-level deck
    learning_deck = client.create_deck("Things To Learn")
    print(f"Created deck: {learning_deck.name}")

    # Create a deck nested inside the first one
    python_deck = client.create_deck("Python Basics", parent_id=learning_deck.id)
    print(f"Created nested deck: {python_deck.name} under {learning_deck.name}")

except MochiAPIError as e:
    print(f"Failed to create deck: {e}")

# --- Updating a Deck ---

# Let's rename the 'Python Basics' deck (assuming 'python_deck' holds the Deck object)
try:
    python_deck.update_deck("Intermediate Python")
    print(f"Deck renamed to: {python_deck.name}")
except MochiAPIError as e:
    print(f"Failed to rename deck: {e}")

# --- Finding Child Decks ---

# Find children of the 'Things To Learn' deck (assuming 'learning_deck' holds the object)
child_names = learning_deck.get_children() # Gets names by default
print(f"Children of '{learning_deck.name}': {child_names}")
# Output: Children of 'Things To Learn': ['Intermediate Python']

child_objects = learning_deck.get_children(names_only=False) # Get full Deck objects
if child_objects:
    print(f"First child object ID: {child_objects[0].id}")

# --- Deleting a Deck (Use with caution!) ---

# To delete the 'Intermediate Python' deck:
# try:
#     # Option 1: Using the client and the ID
#     # client.delete_deck(python_deck.id)
#
#     # Option 2: Using the deck object directly
#     # python_deck.delete()
#
#     print(f"Deck deleted.")
# except MochiAPIError as e:
#     print(f"Failed to delete deck: {e}")