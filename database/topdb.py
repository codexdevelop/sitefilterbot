from info import DATABASE_URI
from info import MOVIE_UPDATE_CHANNEL as CHANNEL_ID
import motor.motor_asyncio
import uuid  # for generating unique IDs

class JsTopDB:
    def __init__(self, db_uri):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(db_uri)
        self.db = self.client["movie_series_db"]
        self.collection = self.db["movie_series"]

    async def set_movie_series_names(self, names, group_id):
        """ Add movies to database and send notification """
        movie_series_list = names.split(",")  # Split input by comma
        for name in movie_series_list:
            search_id = str(uuid.uuid4())  # Generate unique search_id
            await self.collection.update_one(
                {"name": name.strip(), "group_id": group_id},
                {"$inc": {"search_count": 1}},
                upsert=True
            )
            # Notify the channel about the new movie
            await self.notify_update(name.strip())

    async def get_movie_series_names(self, group_id):
        """ Retrieve movie names sorted by search count """
        cursor = self.collection.find({"group_id": group_id})
        cursor.sort("search_count", -1)
        names = [document["name"] async for document in cursor]
        return names

    async def clear_movie_series_names(self, group_id):
        """ Remove all movie names for a group """
        await self.collection.delete_many({"group_id": group_id})

    from pyrogram import Client

    async def notify_update(self, movie_name):
        """ Send a notification to the status channel """
        bot = Client("MovieNotifierBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

        async with bot:  # ✅ Yeh ab async function ke andar hai
            await bot.send_message(CHANNEL_ID, f"**New Movie Added:** {movie_name} 🎬")
# Watch database for real-time changes
async def watch_database():
    """ Continuously watches for new movies and notifies the channel """
    movie_series_db = JsTopDB(DATABASE_URI)
    
    bot = Client("MovieNotifierBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    
    async with bot, movie_series_db.collection.watch() as stream:
        async for change in stream:
            if change["operationType"] == "insert":
                movie_name = change["fullDocument"]["name"]
                await movie_series_db.notify_update(movie_name)

async def main():
    movie_series_db = JsTopDB(DATABASE_URI)
    
    # Start the database watcher in the background
    asyncio.create_task(watch_database())

    while True:
        search_input = input("Enter the movie/series name: ")
        group_id = input("Enter group ID: ")

        # Add movie and auto-notify
        await movie_series_db.set_movie_series_names(search_input, group_id)
        print("✅ Movie/Series Name added & Notification Sent.")

        # Show updated list
        names = await movie_series_db.get_movie_series_names(group_id)
        print("\n🎬 Updated Movie/Series Names (Sorted by Search Count):")
        for name in names:
            print(name)

        # Option to clear data
        clear_input = input("\nDo you want to clear names for this group? (yes/no): ")
        if clear_input.lower() == "yes":
            await movie_series_db.clear_movie_series_names(group_id)
            print("🗑️ Names cleared successfully.")
