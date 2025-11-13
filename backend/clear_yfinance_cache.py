"""
Clear yfinance cache utility script
Run this script to clear yfinance cache and reset session
"""
import os
import shutil
import platform
from pathlib import Path


def clear_yfinance_cache():
    """Clear yfinance cache to reset session and avoid rate limiting"""
    try:
        # Get yfinance cache location based on OS
        system = platform.system()
        user_home = Path.home()
        
        print(f"🖥️ [CACHE] Operating System: {system}")
        print(f"🏠 [CACHE] User Home: {user_home}")
        
        if system == "Windows":
            cache_dir = user_home / "AppData" / "Local" / "py-yfinance"
        elif system == "Linux":
            cache_dir = user_home / ".cache" / "py-yfinance"
        elif system == "Darwin":  # macOS
            cache_dir = user_home / "Library" / "Caches" / "py-yfinance"
        else:
            print(f"⚠️ [CACHE] Unknown OS: {system}, cannot determine cache location")
            return False
        
        print(f"🔍 [CACHE] Looking for cache at: {cache_dir}")
        
        # Check if cache directory exists
        if cache_dir.exists() and cache_dir.is_dir():
            print(f"✅ [CACHE] Found yfinance cache directory")
            
            # List all files
            all_files = list(cache_dir.rglob('*'))
            files = [f for f in all_files if f.is_file()]
            dirs = [d for d in all_files if d.is_dir()]
            
            print(f"📁 [CACHE] Found {len(files)} files and {len(dirs)} directories")
            
            # Show some file names
            if files:
                print(f"📄 [CACHE] Sample files:")
                for f in files[:5]:
                    print(f"   - {f.name}")
                if len(files) > 5:
                    print(f"   ... and {len(files) - 5} more files")
            
            # Ask for confirmation (optional - you can remove this)
            print(f"\n🗑️ [CACHE] Deleting cache directory...")
            
            # Delete cache directory
            shutil.rmtree(cache_dir)
            print(f"✅ [CACHE] Successfully cleared yfinance cache!")
            print(f"   - Deleted {len(files)} files")
            print(f"   - Deleted {len(dirs)} directories")
            return True
        else:
            print(f"ℹ️ [CACHE] No cache found at: {cache_dir}")
            print(f"   Cache directory does not exist - nothing to clear")
            return False
            
    except PermissionError as e:
        print(f"❌ [CACHE] Permission denied: {e}")
        print(f"   Try running as administrator or close any programs using yfinance")
        return False
    except Exception as e:
        print(f"❌ [CACHE] Error clearing yfinance cache: {e}")
        import traceback
        traceback.print_exc()
        return False


def clear_yfinance_session():
    """Clear yfinance session by resetting internal state"""
    try:
        import yfinance as yf
        
        # Try to clear any module-level caches
        try:
            import yfinance.base as yf_base
            if hasattr(yf_base, '_session'):
                yf_base._session = None
                print(f"✅ [SESSION] Cleared yfinance.base._session")
        except Exception as e:
            print(f"⚠️ [SESSION] Could not clear yfinance.base._session: {e}")
        
        try:
            import yfinance.scrapers.quote as yf_quote
            if hasattr(yf_quote, '_session'):
                yf_quote._session = None
                print(f"✅ [SESSION] Cleared yfinance.scrapers.quote._session")
        except Exception as e:
            print(f"⚠️ [SESSION] Could not clear yfinance.scrapers.quote._session: {e}")
            
        print(f"✅ [SESSION] Session clearing attempted")
        return True
    except Exception as e:
        print(f"⚠️ [SESSION] Could not clear session: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🧹 yfinance Cache Clearing Utility")
    print("=" * 60)
    print()
    
    # Clear cache
    cache_result = clear_yfinance_cache()
    print()
    
    # Clear session
    session_result = clear_yfinance_session()
    print()
    
    # Summary
    print("=" * 60)
    if cache_result or session_result:
        print("✅ Cache clearing completed!")
    else:
        print("ℹ️ No cache found or already cleared")
    print("=" * 60)

