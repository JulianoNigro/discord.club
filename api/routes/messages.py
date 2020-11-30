from sanic import Blueprint, response
import bson
import pymongo
from datetime import datetime

from utils import *
from auth import requires_token


bp = Blueprint(name="api.messages", url_prefix="/messages")


@bp.post("/")
@requires_token
@requires_body(
    name=str,
    data=dict,
    files=list
)
async def create_message(request, payload, user_id):
    result = await request.app.db.messages.insert_one({
        "user_id": user_id,
        "last_updated": datetime.utcnow(),
        "name": payload["name"],
        "data": payload["data"],
        "files": payload["files"]
    })
    return {"id": str(result.inserted_id)}


@bp.patch("/<msg_id>")
@requires_token
@requires_body()
async def update_message(request, payload, user_id, msg_id):
    try:
        msg_id = bson.ObjectId(msg_id)
    except bson.errors.InvalidId:
        return response.empty(status=404)

    to_update = {}
    if "name" in payload:
        name = payload["name"]
        if isinstance(name, str):
            to_update["name"] = name

    if "data" in payload:
        data = payload["data"]
        if isinstance(data, dict):
            to_update["data"] = data

    if "files" in payload:
        files = payload["files"]
        if isinstance(files, list):
            to_update["files"] = files

    result = await request.app.db.messages.find_one_and_update(
        {"_id": msg_id, "user_id": user_id},
        {"$set": to_update},
        return_document=pymongo.ReturnDocument.AFTER
    )
    result["id"] = result.pop("_id")
    del result["user_id"]
    return response.json(result)


@bp.delete("/<msg_id>")
@requires_token
async def delete_message(request, user_id, msg_id):
    try:
        msg_id = bson.ObjectId(msg_id)
    except bson.errors.InvalidId:
        return response.empty(status=404)

    await request.app.db.messages.delete_one({"_id": msg_id, "user_id": user_id})
    return response.json({"id": msg_id})


@bp.get("/<msg_id>")
@requires_token
async def get_message(request, user_id, msg_id):
    result = await request.app.db.messages.find_one({"_id": msg_id, "user_id": user_id})
    result["id"] = result.pop("_id")
    del result["user_id"]
    return response.json(result)


@bp.get("/")
@requires_token
async def get_messages(request, user_id):
    messages = []
    async for msg in request.app.db.messages.find_one({"user_id": user_id}):
        messages.append({
            "id": str(msg.pop("_id")),
            "last_updated": msg.pop("last_updated").timestamp(),
            **msg
        })

    return response.json(messages)
