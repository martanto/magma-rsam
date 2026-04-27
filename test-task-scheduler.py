import subprocess
import os
import sys


def create_scheduled_task(
    task_name,
    script_path,
    trigger_times=None,
    trigger_type="daily",
    description="Python script scheduled task",
):
    """
    Create a Windows scheduled task to run a Python script.

    Args:
        task_name: Name of the scheduled task
        script_path: Full path to the Python script
        trigger_times: Single time string or list of times (HH:MM format, 24-hour)
                      e.g., "09:00" or ["09:00", "14:30", "18:00"]
                      Not needed for 'logon' or 'startup' triggers
        trigger_type: Type of trigger (daily, weekly, once, logon, startup)
        description: Description of the task
    """

    # Get Python executable path
    python_exe = sys.executable

    # Expand environment variables in script path
    script_path = os.path.expandvars(script_path)

    # Convert single time to list
    if trigger_times is None:
        trigger_times = ["09:00"]
    elif isinstance(trigger_times, str):
        trigger_times = [trigger_times]

    # Build the PowerShell command
    ps_command = f"""
    $Action = New-ScheduledTaskAction -Execute '{python_exe}' -Argument '{script_path}'
    $Triggers = @()
    """

    # Add triggers based on type
    if trigger_type.lower() in ["daily", "weekly", "once"]:
        for i, time in enumerate(trigger_times):
            if trigger_type.lower() == "daily":
                ps_command += f"""
    $Triggers += New-ScheduledTaskTrigger -Daily -At {time}
    """
            elif trigger_type.lower() == "weekly":
                ps_command += f"""
    $Triggers += New-ScheduledTaskTrigger -Weekly -At {time} -DaysOfWeek Monday
    """
            elif trigger_type.lower() == "once":
                ps_command += f"""
    $Triggers += New-ScheduledTaskTrigger -Once -At {time}
    """
    elif trigger_type.lower() == "logon":
        ps_command += """
    $Triggers += New-ScheduledTaskTrigger -AtLogon
    """
    elif trigger_type.lower() == "startup":
        ps_command += """
    $Triggers += New-ScheduledTaskTrigger -AtStartup
    """
    else:
        print(f"Invalid trigger type: {trigger_type}")
        return False

    # Complete the command
    ps_command += f"""
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName '{task_name}' -Action $Action -Trigger $Triggers -Principal $Principal -Settings $Settings -Description '{description}' -Force
    """

    print(ps_command)

    # try:
    #     # Execute PowerShell command
    #     result = subprocess.run(
    #         ["powershell", "-Command", ps_command],
    #         capture_output=True,
    #         text=True,
    #         check=True,
    #     )
    #
    #     print(f"✓ Task '{task_name}' created successfully!")
    #     print(f"  Script: {script_path}")
    #     if trigger_type.lower() in ["daily", "weekly", "once"]:
    #         print(f"  Trigger: {trigger_type} at {', '.join(trigger_times)}")
    #     else:
    #         print(f"  Trigger: {trigger_type}")
    #     return True
    #
    # except subprocess.CalledProcessError as e:
    #     print(f"✗ Error creating task: {e}")
    #     print(f"Error output: {e.stderr}")
    #     return False


def list_tasks():
    """List all scheduled tasks."""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-ScheduledTask | Select-Object TaskName, State, TaskPath | Format-Table -AutoSize",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        print("Scheduled Tasks:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error listing tasks: {e}")


def remove_task(task_name):
    """Remove a scheduled task."""
    ps_command = f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false"

    try:
        subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✓ Task '{task_name}' removed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error removing task: {e}")
        return False


def get_task_info(task_name):
    """Get information about a specific task."""
    ps_command = (
        f"Get-ScheduledTask -TaskName '{task_name}' | Select-Object * | Format-List"
    )

    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"Task Information for '{task_name}':")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"✗ Error getting task info: {e}")


# Example usage
if __name__ == "__main__":
    # Example 1: Create a task with multiple trigger times
    create_scheduled_task(
        task_name="RunMainPyScript",
        script_path=r"%USERPROFILE%\main.py",
        trigger_times=["09:00", "14:30", "18:00"],  # Runs at 9 AM, 2:30 PM, and 6 PM
        trigger_type="daily",
        description="Runs main.py script three times daily",
    )

    # Example 2: Create a task with single trigger time
    # create_scheduled_task(
    #     task_name="RunMainPyScript",
    #     script_path=r"%USERPROFILE%\main.py",
    #     trigger_times="09:00",  # Single time as string
    #     trigger_type="daily",
    #     description="Runs main.py script daily at 9 AM"
    # )

    # Uncomment below to try other operations:

    # List all tasks
    # list_tasks()

    # Get specific task info
    # get_task_info("RunMainPyScript")

    # Remove task
    # remove_task("RunMainPyScript")
