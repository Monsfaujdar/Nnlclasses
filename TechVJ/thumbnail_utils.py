
"""Persistent default video thumbnail helpers."""
import os
import tempfile
from database.db import db

settings = db.db.thumbnail_settings
KEY = "default_video_thumbnail"


async def get_thumbnail_file_id():
    record = await settings.find_one({"_id": KEY})
    return record.get("file_id") if record else None


async def set_thumbnail_file_id(file_id: str):
    await settings.update_one(
        {"_id": KEY},
        {"$set": {"file_id": file_id}},
        upsert=True,
    )


async def clear_thumbnail_file_id():
    await settings.delete_one({"_id": KEY})


async def download_custom_thumbnail(client):
    """Download and prepare the saved thumbnail when needed."""
    file_id = await get_thumbnail_file_id()
    if not file_id:
        return None

    # Import Pillow only when a thumbnail is actually needed.
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is missing from the running Python environment. "
            "Check the deployment's installed packages."
        ) from exc

    source = await client.download_media(file_id)
    if not source:
        return None

    fd, target = tempfile.mkstemp(
        prefix="bot_thumb_", suffix=".jpg"
    )
    os.close(fd)

    try:
        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail((320, 320))
            image.save(target, "JPEG", quality=82, optimize=True)

        if os.path.getsize(target) > 200 * 1024:
            with Image.open(target) as image:
                image.save(target, "JPEG", quality=50, optimize=True)

        if os.path.getsize(target) > 200 * 1024:
            raise ValueError(
                "Thumbnail exceeds Telegram's 200 KB limit."
            )

        return target

    except Exception:
        try:
            os.remove(target)
        except OSError:
            pass
        raise

    finally:
        try:
            os.remove(source)
        except OSError:
            pass


def remove_thumbnail_file(path):
    if path:
        try:
            os.remove(path)
        except OSError:
            pass
