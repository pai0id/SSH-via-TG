import sys, os, logging, asyncio, subprocess, select
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from fpdf import FPDF

TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))

ADMINS = list(map(int, os.getenv('ADMINS', '').split(';')))

dp = Dispatcher()
router = Router()
dp.include_router(router)

def txt_to_pdf(input_file, output_file):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Courier", size=12)
    
    with open(input_file, "r", encoding="utf-8") as file:
        for line in file:
            pdf.cell(0, 5, txt=line.strip(), ln=True)
    
    pdf.output(output_file)

def emulate_terminal():
    try:
        return subprocess.Popen(
            ["/bin/bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except Exception as e:
        print(f"Error emulating terminal: {e}")
        return None

@router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    if message.chat.id not in ADMINS:
        await message.answer(text="Insufficient permissions")
        return
    data = await state.get_data()
    process = data.get("process", None)
    if process:
        try:
            process.terminate()
            process.wait()
        except Exception as e:
            print(f"Error terminating terminal: {e}")
    process = emulate_terminal()
    await state.update_data(process=process)
    await message.answer(text="Terminal started successfully")

@router.message()
async def command(message: Message, state: FSMContext):
    if message.chat.id not in ADMINS:
        await message.answer(text="Insufficient permissions")
        return
    data = await state.get_data()
    process = data.get("process", None)
    if not process:
        await message.answer(text="Terminal is not running. Use /start to start it.")
        return
    if message.text.lower() in {"exit", "quit"}:
        await message.answer(text="Use /start", reply_markup=ReplyKeyboardRemove())
        return
    cmd = message.text.split('\n')[0]
    stdout, stderr = process.communicate(cmd + "\n")

    with open("./output.txt", "w") as file:
        if stdout:
            file.write(f"stdout:\n{stdout}\n")
        if stderr:
            file.write(f"stderr:\n{stderr}\n")

    txt_to_pdf("output.txt", "output.pdf")

    await bot.send_document(message.chat.id, FSInputFile("output.pdf"))

    os.remove("./output.txt")
    os.remove("./output.pdf")

    if process.returncode == 0:
        await message.answer(text="Command executed successfully!", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer(text=f"Command failed with return code {process.returncode}.", reply_markup=ReplyKeyboardRemove())

    process.terminate()
    process.wait()
    process = emulate_terminal()
    await state.update_data(process=process)

async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())