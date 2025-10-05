#!/usr/bin/env python3
"""
Simple runner for the TerraTrace NASA Supply Chain Platform
"""
import os
import sys
import subprocess

def main():
    """Run the TerraTrace frontend application."""
    print("🚀 Starting NASA TerraTrace - Climate-Smart Supply Chain Platform")
    print("=" * 60)
    
    # Change to the src directory
    os.chdir(os.path.join(os.path.dirname(__file__), 'src'))
    
    # Try to activate virtual environment and run
    try:
        # Check if we're in a virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("✅ Virtual environment detected")
        else:
            print("⚠️  No virtual environment detected - trying to activate...")
            
        # Run the app
        print("🌍 Starting application on http://127.0.0.1:8051")
        print("📊 Loading Swiss Corp supply chain data...")
        print("🗺️  Initializing Zurich-focused map view...")
        print("\n" + "=" * 60)
        
        subprocess.run([sys.executable, 'app.py'], check=True)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Application stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running application: {e}")
        print("\n💡 Try running: source .venv/bin/activate && python src/app.py")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()