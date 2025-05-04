import os
import platform
import asyncio
import subprocess
from datetime import datetime
import shutil

async def open_application(app_name):
    """Opens an application based on the OS and checks if it exists first."""
    system = platform.system()

    # Check if the application is in PATH (for Linux/macOS)
    if system in ["Linux", "Darwin"]:
        if shutil.which(app_name) is None:
            return f"Application '{app_name}' not found."

    try:
        if system == "Windows":
            result = subprocess.run(["where", app_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if not result.stdout.strip():
                return f"Application '{app_name}' not found."
            os.system(f"start {app_name}")

        elif system == "Darwin":  # macOS
            await asyncio.create_subprocess_exec('open','-a', app_name)

        elif system == "Linux":
            subprocess.run([app_name], check=True)

        return f"Opening {app_name}"

    except Exception as e:
        return f"Error opening {app_name}: {e}"


async def get_current_time():
    """Returns the current time as a string."""
    return datetime.now().strftime("%H:%M:%S")


async def execute_command(command):
    """Handles system commands separately."""
    command = command.lower().strip()

    predefined_commands = {
        "time": get_current_time,
        "open chrome": lambda: open_application("chrome"),
        "open spotify": lambda: open_application("spotify"),
        "exit": lambda: asyncio.sleep(0,result="Goodbye!")
    }

    if command in predefined_commands:
        func=predefined_commands[command]
        result=func()
        if asyncio.iscoroutine(result):
            return await result
        return result

    elif command.startswith("open "):  # Open other applications dynamically
        app_name = command.replace("open ", "").strip()
        return open_application(app_name)


    return None  # Return None if it's not a system command
