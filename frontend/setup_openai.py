#!/usr/bin/env python3
"""
Setup script for OpenAI integration with Swiss Corp Assistant
"""

import os
import subprocess
import sys

def install_openai():
    """Install OpenAI package if not already installed."""
    try:
        import openai
        print("✅ OpenAI package is already installed")
        return True
    except ImportError:
        print("📦 Installing OpenAI package...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
            print("✅ OpenAI package installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install OpenAI package: {e}")
            return False

def setup_api_key():
    """Help user set up OpenAI API key."""
    current_key = os.getenv("OPENAI_API_KEY")
    
    if current_key:
        print(f"✅ OpenAI API key is already set: {current_key[:8]}...{current_key[-4:]}")
        return True
    
    print("\n🔑 OpenAI API Key Setup")
    print("=" * 50)
    print("You need to set your OpenAI API key as an environment variable.")
    print("\nOptions:")
    print("1. Set for current session:")
    print("   export OPENAI_API_KEY='your-api-key-here'")
    print("\n2. Set permanently in your shell profile (~/.bashrc, ~/.zshrc):")
    print("   echo 'export OPENAI_API_KEY=\"your-api-key-here\"' >> ~/.zshrc")
    print("\n3. Create a .env file in the frontend directory:")
    print("   echo 'OPENAI_API_KEY=your-api-key-here' > .env")
    
    api_key = input("\n🔑 Enter your OpenAI API key (or press Enter to skip): ").strip()
    
    if api_key:
        # Set for current session
        os.environ["OPENAI_API_KEY"] = api_key
        
        # Create .env file
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        with open(env_file, "w") as f:
            f.write(f"OPENAI_API_KEY={api_key}\n")
        
        print(f"✅ API key set and saved to {env_file}")
        return True
    else:
        print("⚠️  Skipping API key setup. You'll need to set it manually.")
        return False

def main():
    print("🚀 Swiss Corp Assistant - OpenAI Setup")
    print("=" * 50)
    
    # Install OpenAI package
    if not install_openai():
        return
    
    # Setup API key
    setup_api_key()
    
    print("\n🎉 Setup complete!")
    print("\nTo run the app with OpenAI integration:")
    print("1. Make sure your API key is set")
    print("2. Run: python -m src.app")
    print("\nThe chat assistant will now use real OpenAI GPT responses!")

if __name__ == "__main__":
    main()