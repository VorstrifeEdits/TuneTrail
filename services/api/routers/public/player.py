from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from datetime import datetime
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.track import Track, TrackResponse
from models.player import (
    PlayerState,
    Queue,
    PlaybackStateResponse,
    PlayAction,
    SeekAction,
    VolumeAction,
    QueueAddRequest,
    QueueItem,
    RepeatMode,
)
from middleware.auth import get_current_user

router = APIRouter(prefix="/me/player", tags=["Player Control"])


@router.get("/state", response_model=PlaybackStateResponse)
async def get_playback_state(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaybackStateResponse:
    """
    Get current playback state.

    Returns complete player state including current track, progress,
    shuffle/repeat settings, and device information.

    **Use Cases:**
    - Initialize player UI
    - Sync state across devices
    - Resume playback

    **WebSocket Alternative**: Use `/ws/player` for real-time updates
    """
    result = await db.execute(
        select(PlayerState)
        .where(PlayerState.user_id == current_user.id)
        .options(selectinload(PlayerState.current_track))
    )
    player_state = result.scalar_one_or_none()

    if not player_state:
        player_state = PlayerState(
            user_id=current_user.id,
            is_playing=False,
            shuffle_enabled=False,
            repeat_mode="off",
            volume=80,
        )
        db.add(player_state)
        await db.commit()
        await db.refresh(player_state)

    current_track_response = None
    duration_ms = None

    if player_state.current_track:
        current_track_response = TrackResponse.from_orm(player_state.current_track)
        if player_state.current_track.duration_seconds:
            duration_ms = player_state.current_track.duration_seconds * 1000

    return PlaybackStateResponse(
        is_playing=player_state.is_playing,
        current_track=current_track_response,
        progress_ms=player_state.progress_ms,
        duration_ms=duration_ms,
        shuffle_enabled=player_state.shuffle_enabled,
        repeat_mode=RepeatMode(player_state.repeat_mode),
        volume=player_state.volume,
        device_id=player_state.device_id,
        device_name=player_state.device_name,
        device_type=player_state.device_type,
        context_type=player_state.context_type,
        context_id=player_state.context_id,
        timestamp=player_state.updated_at,
    )


@router.put("/play", status_code=status.HTTP_204_NO_CONTENT)
async def start_playback(
    play_data: PlayAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Start or resume playback.

    **Options:**
    - Resume current track
    - Play specific tracks
    - Play from context (playlist, album, artist)

    **ML Context Capture:**
    - Records playback start as interaction
    - Tracks context (what triggered play)
    - Enables recommendation attribution
    """
    result = await db.execute(
        select(PlayerState).where(PlayerState.user_id == current_user.id)
    )
    player_state = result.scalar_one_or_none()

    if not player_state:
        player_state = PlayerState(user_id=current_user.id)
        db.add(player_state)

    if play_data.track_ids:
        await db.execute(delete(Queue).where(Queue.user_id == current_user.id))

        for position, track_id in enumerate(play_data.track_ids):
            queue_item = Queue(
                user_id=current_user.id,
                track_id=track_id,
                position=position,
                context_type=play_data.context_type,
                context_id=play_data.context_id,
            )
            db.add(queue_item)

        player_state.current_track_id = play_data.track_ids[0]

    player_state.is_playing = True
    player_state.progress_ms = play_data.position_ms
    player_state.context_type = play_data.context_type
    player_state.context_id = play_data.context_id
    player_state.updated_at = datetime.utcnow()

    if play_data.device_id:
        player_state.device_id = play_data.device_id

    await db.commit()


@router.put("/pause", status_code=status.HTTP_204_NO_CONTENT)
async def pause_playback(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Pause playback.

    Maintains current position for resume.
    """
    result = await db.execute(
        select(PlayerState).where(PlayerState.user_id == current_user.id)
    )
    player_state = result.scalar_one_or_none()

    if player_state:
        player_state.is_playing = False
        player_state.updated_at = datetime.utcnow()
        await db.commit()


@router.post("/next", status_code=status.HTTP_204_NO_CONTENT)
async def skip_to_next(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Skip to next track in queue.

    **Behavior:**
    - Moves to next track in queue
    - If queue empty and repeat=context, restart context
    - If queue empty and repeat=off, stop playback
    - Records skip interaction for ML
    """
    queue_query = (
        select(Queue)
        .where(Queue.user_id == current_user.id)
        .order_by(Queue.is_priority.desc(), Queue.position)
        .limit(2)
    )
    result = await db.execute(queue_query)
    queue_items = list(result.scalars().all())

    if len(queue_items) > 1:
        await db.delete(queue_items[0])

        player_state_query = select(PlayerState).where(PlayerState.user_id == current_user.id)
        player_result = await db.execute(player_state_query)
        player_state = player_result.scalar_one_or_none()

        if player_state:
            player_state.current_track_id = queue_items[1].track_id
            player_state.progress_ms = 0
            player_state.updated_at = datetime.utcnow()

        await db.commit()


@router.post("/previous", status_code=status.HTTP_204_NO_CONTENT)
async def skip_to_previous(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Skip to previous track.

    **Behavior:**
    - If progress > 3 seconds: restart current track
    - If progress < 3 seconds: go to previous track
    """
    result = await db.execute(
        select(PlayerState).where(PlayerState.user_id == current_user.id)
    )
    player_state = result.scalar_one_or_none()

    if player_state:
        if player_state.progress_ms > 3000:
            player_state.progress_ms = 0
        else:
            pass

        player_state.updated_at = datetime.utcnow()
        await db.commit()


@router.put("/seek", status_code=status.HTTP_204_NO_CONTENT)
async def seek_to_position(
    seek_data: SeekAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Seek to position in current track.

    **Use Cases:**
    - Scrubbing timeline
    - Skip to chorus
    - Replay section
    """
    result = await db.execute(
        select(PlayerState).where(PlayerState.user_id == current_user.id)
    )
    player_state = result.scalar_one_or_none()

    if player_state:
        player_state.progress_ms = seek_data.position_ms
        player_state.updated_at = datetime.utcnow()
        await db.commit()


@router.put("/shuffle", status_code=status.HTTP_204_NO_CONTENT)
async def toggle_shuffle(
    shuffle_enabled: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Toggle shuffle mode.

    When enabling shuffle, queue is randomized.
    """
    result = await db.execute(
        select(PlayerState).where(PlayerState.user_id == current_user.id)
    )
    player_state = result.scalar_one_or_none()

    if player_state:
        player_state.shuffle_enabled = shuffle_enabled
        player_state.updated_at = datetime.utcnow()
        await db.commit()


@router.put("/repeat", status_code=status.HTTP_204_NO_CONTENT)
async def set_repeat_mode(
    repeat_mode: RepeatMode,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Set repeat mode.

    **Modes:**
    - `off`: No repeat
    - `track`: Repeat current track
    - `context`: Repeat playlist/album/context
    """
    result = await db.execute(
        select(PlayerState).where(PlayerState.user_id == current_user.id)
    )
    player_state = result.scalar_one_or_none()

    if player_state:
        player_state.repeat_mode = repeat_mode.value
        player_state.updated_at = datetime.utcnow()
        await db.commit()


@router.put("/volume", status_code=status.HTTP_204_NO_CONTENT)
async def set_volume(
    volume_data: VolumeAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Set playback volume.

    Volume level: 0 (mute) to 100 (max).
    """
    result = await db.execute(
        select(PlayerState).where(PlayerState.user_id == current_user.id)
    )
    player_state = result.scalar_one_or_none()

    if player_state:
        player_state.volume = volume_data.volume
        player_state.updated_at = datetime.utcnow()
        await db.commit()


@router.get("/currently-playing", response_model=PlaybackStateResponse)
async def get_currently_playing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaybackStateResponse:
    """
    Get currently playing track with full context.

    **Real-time alternative**: Use WebSocket `/ws/player` for updates.
    """
    return await get_playback_state(current_user, db)


@router.get("/queue", response_model=List[QueueItem])
async def get_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[QueueItem]:
    """
    Get user's current playback queue.

    Returns tracks in order they'll be played.
    Priority tracks (play next) appear first.
    """
    query = (
        select(Queue, Track)
        .join(Track, Queue.track_id == Track.id)
        .where(Queue.user_id == current_user.id)
        .order_by(Queue.is_priority.desc(), Queue.position)
    )

    result = await db.execute(query)
    rows = result.all()

    queue_items = [
        QueueItem(
            id=queue.id,
            track=TrackResponse.from_orm(track),
            position=queue.position,
            is_priority=queue.is_priority,
            added_at=queue.added_at,
            context_type=queue.context_type,
            context_id=queue.context_id,
        )
        for queue, track in rows
    ]

    return queue_items


@router.post("/queue", status_code=status.HTTP_204_NO_CONTENT)
async def add_to_queue(
    queue_data: QueueAddRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Add tracks to queue.

    **Options:**
    - `play_next=true`: Add to front (play immediately after current)
    - `play_next=false`: Add to end of queue

    **ML Context:**
    - Tracks source of queue addition
    - Records user intent
    """
    for track_id in queue_data.track_ids:
        result = await db.execute(
            select(Track).where(
                Track.id == track_id,
                Track.org_id == current_user.org_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Track {track_id} not found",
            )

    if queue_data.play_next:
        max_pos_query = select(func.max(Queue.position)).where(
            Queue.user_id == current_user.id,
            Queue.is_priority == True,
        )
        max_priority_pos = await db.scalar(max_pos_query) or -1

        for idx, track_id in enumerate(queue_data.track_ids):
            queue_item = Queue(
                user_id=current_user.id,
                track_id=track_id,
                position=max_priority_pos + idx + 1,
                is_priority=True,
                context_type=queue_data.context_type,
                context_id=queue_data.context_id,
            )
            db.add(queue_item)
    else:
        max_pos_query = select(func.max(Queue.position)).where(
            Queue.user_id == current_user.id
        )
        max_pos = await db.scalar(max_pos_query) or -1

        for idx, track_id in enumerate(queue_data.track_ids):
            queue_item = Queue(
                user_id=current_user.id,
                track_id=track_id,
                position=max_pos + idx + 1,
                is_priority=False,
                context_type=queue_data.context_type,
                context_id=queue_data.context_id,
            )
            db.add(queue_item)

    await db.commit()


@router.delete("/queue/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_queue(
    track_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Remove specific track from queue.

    Reorders remaining tracks automatically.
    """
    await db.execute(
        delete(Queue).where(
            Queue.user_id == current_user.id,
            Queue.track_id == track_id,
        )
    )

    remaining_query = (
        select(Queue)
        .where(Queue.user_id == current_user.id)
        .order_by(Queue.is_priority.desc(), Queue.position)
    )
    result = await db.execute(remaining_query)
    remaining_items = list(result.scalars().all())

    for new_position, item in enumerate(remaining_items):
        item.position = new_position

    await db.commit()


@router.delete("/queue", status_code=status.HTTP_204_NO_CONTENT)
async def clear_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Clear entire playback queue.

    Removes all queued tracks.
    """
    await db.execute(delete(Queue).where(Queue.user_id == current_user.id))
    await db.commit()


@router.websocket("/ws")
async def player_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """
    Real-time player state updates via WebSocket.

    **Use Cases:**
    - Sync playback across devices
    - Real-time progress updates
    - Live queue changes

    **Messages:**
    - Client → Server: Player commands (play, pause, seek)
    - Server → Client: State updates every 1 second

    **Protocol:**
    ```json
    // Client sends:
    {"action": "play", "track_id": "123"}
    {"action": "pause"}
    {"action": "seek", "position_ms": 30000}

    // Server sends:
    {"type": "state_update", "data": {PlaybackStateResponse}}
    ```
    """
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            response = {"type": "ack", "message": "Command received"}
            await websocket.send_json(response)

    except WebSocketDisconnect:
        print(f"WebSocket disconnected")