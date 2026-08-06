# main.py

from dotenv import load_dotenv
from scripts.setup_infrastructure import SystemInitializer
from scripts import menu

def main():
    # 1. Load environment variables from .env if they exist
    load_dotenv()
    
    # 2. Run the full system infrastructure and agent setup
    initializer = SystemInitializer()
    initializer.run_full_initialization()
    
    # 3. Start the CLI main menu
    menu.run_main_menu()

if __name__ == "__main__":
    main()
