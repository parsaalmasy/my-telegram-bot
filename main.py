import os
import uuid
import subprocess
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = "7890200404:AAETXFo7lmMXMpKXDm7XOb43Xl8q0yZARcI"

# Ensure 'downloads' folder exists
os.makedirs("downloads", exist_ok=True)

async def start(update: Update, context: CallbackContext):
    """Sends a welcome message with the user's name."""
    user_name = update.effective_user.first_name  # Get user's first name
    await update.message.reply_text(f"سلام {user_name} خوش اومدی! 🎉\n\nویدیویی که می‌خوای به ویدیومسیج تبدیل بشه رو بفرست 🎥")

async def convert_video(update: Update, context: CallbackContext):
    """Converts a received video into a Telegram video message (circular format)."""
    message = update.message
    video = None

    if message.video:
        video = message.video
    elif message.document and message.document.mime_type.startswith("video/"):
        video = message.document
    else:
        return

    # Check if the video duration is more than 60 seconds
    if video.duration and video.duration > 60:
        await update.message.reply_text("⛔ ویدیو بیش از 60 ثانیه است. لطفاً یک ویدیوی کوتاه‌تر ارسال کنید.")
        return

    # Send processing message and store its reference
    processing_msg = await update.message.reply_text("🎥 در حال تبدیل ویدیو به ویدیومسیج... لطفاً صبر کنید ⏳")

    # Generate unique file names
    unique_id = str(uuid.uuid4())
    input_path = f"downloads/{unique_id}_input.mp4"
    output_path = f"downloads/{unique_id}_output.mp4"
    
    file = await video.get_file()
    await file.download_to_drive(input_path)

    # FFmpeg command for round video conversion
    command = [
        "ffmpeg", "-i", input_path, "-vf",
        "scale=640:640:force_original_aspect_ratio=decrease,pad=640:640:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-b:v", "1M", "-c:v", "libx264", "-preset", "fast", "-crf", "28", "-y", output_path
    ]

    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command, process.stdout, process.stderr)
    except subprocess.TimeoutExpired:
        await processing_msg.edit_text("⏳ پردازش ویدیو زمان زیادی برد! لطفاً ویدیوی کوتاه‌تری ارسال کنید.")
        return
    except subprocess.CalledProcessError as e:
        print("FFmpeg error:", e.stderr)
        await processing_msg.edit_text("❌ خطایی در تبدیل ویدیو رخ داد. لطفاً ویدیو را بررسی کنید.")
        return

    # Delete the processing message after conversion
    await processing_msg.delete()

    # Send video note
    with open(output_path, "rb") as video_file:
        await update.message.reply_video_note(video_note=InputFile(video_file))

    # Clean up files
    os.remove(input_path)
    os.remove(output_path)

# Create the bot application
app = Application.builder().token(TOKEN).build()

# Add command and message handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, convert_video))

# Start the bot
if __name__ == "__main__":
    print("Bot is running...")
    app.run_polling(timeout=30, read_timeout=30, write_timeout=30)
