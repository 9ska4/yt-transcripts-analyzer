# guest_calculator.py

def calculate_guest(channel_handle, title, description):
    """
    Calculates the guest field based on channelHandle, title, and description.

    Args:
        channel_handle (str): The handle of the YouTube channel.
        title (str): The title of the video.
        description (str): The description of the video.

    Returns:
        str: The calculated guest string.
    """
    # All should be strings!
    if not isinstance(channel_handle, str):
        channel_handle = str(channel_handle) if channel_handle is not None else ''
    if not isinstance(title, str):
        title = str(title) if title is not None else ''
    if not isinstance(description, str):
        description = str(description) if description is not None else ''

    # todo: code me, dummy logic now
    first_word_title = title.split()[0] if title.strip() else ''
    first_word_description = description.split()[0] if description.strip() else ''
    guest_parts = [channel_handle.strip()]

    if first_word_title:
        guest_parts.append(first_word_title[:20])
    if first_word_description:
        guest_parts.append(first_word_description[:20])

    guest = ' '.join(guest_parts)

    return guest
