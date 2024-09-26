import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, ConversationHandler, filters
from pdf2image import convert_from_path
import pytesseract
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define states for the ConversationHandler
BUILDING_TYPE, LOCATION, FIRE_SAFETY, CUSTOMER_ID, DOCUMENTS, CONFIRM = range(6)

# Define allowed file extensions for documents
ALLOWED_FILE_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

# Ensure the output_images directory exists
os.makedirs('output_images', exist_ok=True)

# Path to Poppler for PDF to image conversion
POPPLER_PATH = r'C:\Users\ankit\Downloads\Release-24.07.0-0\poppler-24.07.0\Library\bin'

# Function to perform OCR on an image
def perform_ocr(image_path: str) -> str:
    try:
        logger.info("Performing OCR on: %s", image_path)
        text = pytesseract.image_to_string(image_path)
        logger.info("OCR result: %s", text)
        return text
    except Exception as e:
        logger.error("Error performing OCR: %s", str(e))
        return "Error processing image."

# Function to process PDF files
def process_pdf(pdf_path: str) -> None:
    logger.info("Processing PDF file: %s", pdf_path)
    try:
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
        logger.info("Number of pages in PDF: %d", len(images))
        for i, image in enumerate(images):
            image_path = f'output_images/page_{i}.jpg'
            image.save(image_path, 'JPEG')
            logger.info("Saved PDF page to: %s", image_path)
            
            # Perform OCR on each image
            ocr_text = perform_ocr(image_path)
            logger.info("OCR text for page %d: %s", i, ocr_text)
    except Exception as e:
        logger.error("Error processing PDF: %s", str(e))

# Function to handle /start command
async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Welcome! Please enter the building type:")
    return BUILDING_TYPE

# Function to handle building type input
async def building_type(update: Update, context: CallbackContext) -> int:
    context.user_data['building_type'] = update.message.text
    await update.message.reply_text("Please enter the location:")
    return LOCATION

# Function to handle location input
async def location(update: Update, context: CallbackContext) -> int:
    context.user_data['location'] = update.message.text
    await update.message.reply_text("Please enter the fire safety measures:")
    return FIRE_SAFETY

# Function to handle fire safety measures input
async def fire_safety(update: Update, context: CallbackContext) -> int:
    context.user_data['fire_safety'] = update.message.text
    await update.message.reply_text("Please enter your customer ID:")
    return CUSTOMER_ID

# Function to handle customer ID input
async def customer_id(update: Update, context: CallbackContext) -> int:
    context.user_data['customer_id'] = update.message.text
    await update.message.reply_text("Please upload the relevant documents:")
    return DOCUMENTS

# Function to handle document upload
async def documents(update: Update, context: CallbackContext) -> int:
    document = update.message.document

    if document:
        file = await document.get_file()
        file_path = f'output_images/{document.file_name}'
        file_extension = file_path.split('.')[-1].lower()

        if file_extension in ALLOWED_FILE_EXTENSIONS:
            await file.download_to_drive(file_path)
            logging.info("Document received and saved: %s", file_path)
            context.user_data['documents'] = file_path

            if file_extension in ['jpg', 'jpeg', 'png']:
                ocr_text = perform_ocr(file_path)
                context.user_data['ocr_text'] = ocr_text
                await update.message.reply_text(f"OCR Result: {ocr_text}\n\nDocuments received successfully. Please confirm your submission (yes/no):")
            elif file_extension == 'pdf':
                process_pdf(file_path)
                await update.message.reply_text("PDF received and processed. Please confirm your submission (yes/no):")
            else:
                await update.message.reply_text("Document type not supported.")
                return DOCUMENTS

            return CONFIRM
        else:
            await update.message.reply_text("Invalid file type. Please upload PDF, JPG, or PNG only.")
            return DOCUMENTS
    else:
        await update.message.reply_text("Please upload valid documents.")
        return DOCUMENTS

# Function to handle confirmation of submission
async def confirm(update: Update, context: CallbackContext) -> int:
    confirmation = update.message.text.lower()
    if confirmation == 'yes':
        await update.message.reply_text("Thank you! Your submission has been received.")
        return ConversationHandler.END
    elif confirmation == 'no':
        await update.message.reply_text("Submission cancelled. You can start over by sending /start.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Please reply with 'yes' or 'no'.")
        return CONFIRM

# Function to handle /cancel command
async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Operation cancelled. You can start over by sending /start.")
    return ConversationHandler.END

# Custom filter for documents
def document_filter(message) -> bool:
    document = message.document
    if document:
        file_extension = document.file_name.split('.')[-1].lower()
        return file_extension in ALLOWED_FILE_EXTENSIONS
    return False

# Main function to start the bot
def main():
    # Use your bot token from BotFather
    application = Application.builder().token("Your bot token").build()

    # Conversation handler for managing the flow of the bot
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            BUILDING_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, building_type)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location)],
            FIRE_SAFETY: [MessageHandler(filters.TEXT & ~filters.COMMAND, fire_safety)],
            CUSTOMER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, customer_id)],
            DOCUMENTS: [MessageHandler(filters.Document.ALL, documents)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)

    # Start the bot
    logging.info("Starting the bot.")
    application.run_polling()

if __name__ == '__main__':
    main()
