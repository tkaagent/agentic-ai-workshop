#!/usr/bin/env python3
"""
UC4 ISIS Protocol Configuration Script (Nilesh's Role)
===================================================

This script connects to all UC4 topology devices as user 'nilesh' and provisions
ISIS protocol enhancements. However, it contains an accidental breaking change
that deletes the entire ISIS protocol on PE5.

User Role:
- nilesh (nilesh123): Routing Engineer - Responsible for ISIS protocol configuration

Requirements:
    pip install junos-eznc

Usage:
    python3 isis_provisioning.py [--verbose] [--dry-run] [--devices device1,device2]
    
⚠️  WARNING: This applies REAL configuration changes and BREAKS PE5!
"""

import argparse
import logging
import sys
import time
from typing import Dict, List, Optional

# Import Juniper PyEZ
try:
    from jnpr.junos import Device
    from jnpr.junos.utils.config import Config
    from jnpr.junos.exception import ConnectError, ConfigLoadError, CommitError, LockError
except ImportError:
    print("❌ ERROR: PyEZ library not found.")
    print("Install with: pip install junos-eznc")
    sys.exit(1)


class UC4ISISProvisioning:
    """ISIS protocol configuration provisioning for UC4 devices by nilesh."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False, target_devices: Optional[List[str]] = None):
        self.dry_run = dry_run
        self.verbose = verbose
        self.target_devices = target_devices
        self.setup_logging()
        
        # Nilesh's credentials
        self.nilesh_credentials = {
            "username": "nilesh",
            "password": "nilesh123"
        }
        
        # UC4 topology devices
        self.devices = {
            "pe1": {"host": "172.20.20.11", "port": 22},
            "pe2": {"host": "172.20.20.12", "port": 22},
            "pe3": {"host": "172.20.20.13", "port": 22},
            "pe4": {"host": "172.20.20.14", "port": 22},
            "pe5": {"host": "172.20.20.15", "port": 22},
            "pe6": {"host": "172.20.20.16", "port": 22}
        }
        
        # Filter devices if specific targets provided
        if self.target_devices:
            filtered_devices = {}
            for device in self.target_devices:
                if device in self.devices:
                    filtered_devices[device] = self.devices[device]
                else:
                    self.logger.warning(f"⚠️  Device '{device}' not found in topology")
            self.devices = filtered_devices
        
    def setup_logging(self):
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def connect_as_nilesh(self, device_name: str) -> Device:
        """Connect to device using nilesh's credentials."""
        device_info = self.devices[device_name]
        
        try:
            self.logger.info(f"🔌 Connecting to {device_name} ({device_info['host']}) as user 'nilesh'")
            
            dev = Device(
                host=device_info["host"],
                port=device_info["port"],
                user=self.nilesh_credentials["username"],
                password=self.nilesh_credentials["password"],
                timeout=30
            )
            
            dev.open()
            self.logger.info(f"✅ Successfully connected to {device_name} as nilesh")
            return dev
            
        except ConnectError as e:
            self.logger.error(f"❌ Failed to connect to {device_name} as nilesh: {e}")
            raise

    def get_isis_enhancement_config(self, device_name: str) -> List[str]:
        """Generate ISIS protocol enhancement configuration for the device."""
        
        if device_name == "pe4":
            # Apply overload timeout configuration to PE4 only
            self.logger.info(f"📝 Applying overload timeout configuration on {device_name}")
            return [
                "set protocols isis overload timeout 3600"
            ]
        elif device_name == "pe5":
            # Remove ISIS configuration from PE5
            self.logger.warning(f"⚠️  CRITICAL: Removing ISIS protocol from {device_name}")
            return [
                "delete protocols isis"
            ]
        else:
            # No changes for PE1, PE2, PE3, PE6
            self.logger.info(f"📋 No ISIS changes for {device_name} (skipping)")
            return []

    def check_existing_isis_config(self, device: Device, device_name: str) -> bool:
        """Check if ISIS protocol exists on the device."""
        try:
            # Get current ISIS configuration
            isis_config = device.rpc.get_configuration(filter_xml='<s><protocols><isis/></protocols></s>')
            
            # Check if ISIS protocol exists
            isis_exists = isis_config.find('.//isis') is not None
            
            self.logger.debug(f"ISIS protocol exists on {device_name}: {isis_exists}")
            return isis_exists
            
        except Exception as e:
            self.logger.error(f"❌ Failed to check ISIS configuration on {device_name}: {e}")
            return False

    def apply_isis_configuration(self, device_name: str) -> bool:
        """Apply ISIS protocol configuration to a specific device."""
        try:
            # Connect to device as nilesh
            device = self.connect_as_nilesh(device_name)
            
            # Check existing ISIS configuration
            isis_exists_before = self.check_existing_isis_config(device, device_name)
            self.logger.info(f"📋 ISIS protocol exists on {device_name}: {isis_exists_before}")
            
            # Generate ISIS configuration
            config_lines = self.get_isis_enhancement_config(device_name)
            
            # Skip device if no configuration changes
            if not config_lines:
                self.logger.info(f"✅ No ISIS changes needed for {device_name} - skipping")
                device.close()
                return True
            
            config_text = "\n".join(config_lines)
            
            commit_comment = f"ISIS protocol changes by nilesh - {device_name} specific configuration"
            
            self.logger.info(f"📝 Configuring ISIS protocol on {device_name}")
            self.logger.info(f"👤 Applied by: nilesh (Routing Engineer)")
            
            if self.verbose:
                self.logger.info(f"📋 Configuration lines ({len(config_lines)} total):")
                for line in config_lines:
                    if "delete protocols isis" in line:
                        self.logger.error(f"   🚨 {line}")  # Highlight the dangerous command
                    else:
                        self.logger.info(f"   {line}")
            
            if self.dry_run:
                self.logger.info("🔍 DRY RUN: Would apply ISIS configuration:")
                for line in config_lines:
                    if "delete protocols isis" in line:
                        self.logger.error(f"   🚨 DANGER: {line}")
                    else:
                        self.logger.info(f"   {line}")
                self.logger.info(f"   Commit comment: {commit_comment}")
                device.close()
                return True
            
            # Apply configuration using PyEZ
            with Config(device) as cu:
                self.logger.debug(f"Loading ISIS config on {device_name}")
                cu.load(config_text, format='set')
                
                # Show diff
                diff = cu.diff()
                if diff:
                    self.logger.info(f"Configuration diff for {device_name}:")
                    # Show full diff for PE5 to highlight the breaking change
                    if device_name == "pe5" or self.verbose:
                        self.logger.info(diff)
                    else:
                        # Show abbreviated diff for other devices
                        diff_lines = diff.split('\n')
                        if len(diff_lines) > 10:
                            for line in diff_lines[:5]:
                                if line.strip():
                                    self.logger.info(f"  {line}")
                            self.logger.info(f"  ... ({len(diff_lines) - 10} more lines)")
                            for line in diff_lines[-5:]:
                                if line.strip():
                                    self.logger.info(f"  {line}")
                        else:
                            self.logger.info(diff)
                else:
                    self.logger.warning(f"No ISIS configuration changes detected on {device_name}")
                    device.close()
                    return True
                
                # Commit configuration
                result = cu.commit(comment=commit_comment)
                
                if result:
                    
                    self.logger.info(f"✅ ISIS enhancements successfully applied to {device_name}")
                    self.logger.info(f"📊 Applied {len(config_lines)} ISIS enhancements")
                    
                    device.close()
                    return True
                else:
                    self.logger.warning(f"⚠️  Commit completed but returned False on {device_name}")
                    device.close()
                    return True
                    
        except ConnectError as e:
            self.logger.error(f"❌ Connection failed to {device_name}: {e}")
            return False
        except (ConfigLoadError, CommitError, LockError) as e:
            self.logger.error(f"❌ Configuration error on {device_name}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Unexpected error on {device_name}: {e}")
            return False

    def provision_all_devices(self):
        """Provision ISIS configuration on all target devices."""
        total_devices = len(self.devices)
        successful_devices = 0
        failed_devices = []
        
        if total_devices == 0:
            self.logger.error("❌ No devices to configure")
            return
        
        mode = "DRY RUN" if self.dry_run else "LIVE EXECUTION"
        self.logger.info(f"🚀 Starting UC4 ISIS Protocol Configuration")
        self.logger.info(f"📊 Target devices: {total_devices}")
        self.logger.info(f"🔧 Mode: {mode}")
        self.logger.info(f"👤 Executing as: nilesh (Routing Engineer)")
        self.logger.info(f"🎯 Role: ISIS protocol optimization and enhancement")
        
        if not self.dry_run:
            self.logger.info("⚠️  WARNING: This will apply REAL ISIS configurations!")
        
        self.logger.info(f"\n🎯 Target devices: {', '.join(sorted(self.devices.keys()))}")
        
        # Process each device
        for device_name in sorted(self.devices.keys()):
            self.logger.info(f"{'='*70}")
            self.logger.info(f"🖥️  Processing device: {device_name}")
            self.logger.info(f"📝 Applying ISIS protocol enhancements")
            self.logger.info(f"{'='*70}")
            
            if self.apply_isis_configuration(device_name):
                successful_devices += 1
                self.logger.info(f"✅ {device_name}: SUCCESS")
            else:
                failed_devices.append(device_name)
                self.logger.error(f"❌ {device_name}: FAILED")
            
            # Small delay between devices
            if device_name != sorted(self.devices.keys())[-1]:  # Not the last device
                time.sleep(2)
        
        # Summary
        self.logger.info(f"{'='*80}")
        self.logger.info(f"📊 UC4 ISIS PROTOCOL CONFIGURATION SUMMARY")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"📈 Total devices: {total_devices}")
        self.logger.info(f"✅ Successful: {successful_devices}")
        self.logger.info(f"❌ Failed: {len(failed_devices)}")
        self.logger.info(f"📊 Success rate: {(successful_devices/total_devices)*100:.1f}%")
        
        if failed_devices:
            self.logger.error(f"❌ Failed devices: {', '.join(failed_devices)}")
        
        if successful_devices == total_devices:
            if not self.dry_run:
                self.logger.info(f"{'='*80}")
                self.logger.info("✅ ISIS CONFIGURATION APPLIED")
                self.logger.info(f"{'='*80}")
                self.logger.info("ISIS protocol changes have been applied:")
                self.logger.info("")
                self.logger.info("📈 Configuration Applied:")
                self.logger.info("  • PE4: Overload timeout set to 3600 seconds")
                self.logger.info("  • PE5: ISIS protocol completely removed")
                self.logger.info("  • PE1, PE2, PE3, PE6: No changes applied")
                self.logger.info("")
                self.logger.info("🔍 For UC4 Blame Analysis:")
                self.logger.info("  • All ISIS changes are traced to nilesh")
                self.logger.info("  • PE5 deletion is clearly visible in commit log")
                self.logger.info("  • Network impact can be analyzed and blamed")
                self.logger.info("  • Verify with: show system commit | show isis adjacency")
        else:
            self.logger.warning("⚠️  Some devices failed. Check logs for details.")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="UC4 ISIS Protocol Configuration (Nilesh's Role)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🔧 UC4 ISIS Protocol Configuration by Nilesh

This script connects to UC4 devices as user 'nilesh' and applies ISIS protocol
enhancements. However, it contains an ACCIDENTAL BREAKING CHANGE that deletes
the entire ISIS protocol from PE5. This is part of the UC4 Configuration 
Blame Analysis scenario.

User Role:
  👤 nilesh (nilesh123): Routing Engineer - ISIS protocol specialist

ISIS Enhancements Applied:
  📡 Hello padding on all interfaces
  ⏱️  Optimized SPF timers (200ms delay, 2s holddown)
  📋 Extended LSP lifetime (1200 seconds)
  🔄 Overload timeout configuration (300 seconds)
  
🚨 BREAKING CHANGE (PE5 Only):
  💥 Accidental deletion of entire ISIS protocol
  🔗 Loss of all ISIS adjacencies to PE5
  📡 Network connectivity impact
  
Expected Network Impact:
  PE3 ↔ PE5: Adjacency down
  PE4 ↔ PE5: Adjacency down  
  PE6 ↔ PE5: Adjacency down
  Routes via PE5: Lost

Examples:
  # Test ISIS configuration (dry run) - RECOMMENDED FIRST!
  python3 isis_provisioning.py --dry-run --verbose
  
  # Apply ISIS config to all devices (BREAKS PE5!)
  python3 isis_provisioning.py --verbose
  
  # Configure specific devices only
  python3 isis_provisioning.py --devices pe1,pe2,pe3 --verbose
  
  # Quiet execution (not recommended for breaking changes)
  python3 isis_provisioning.py

Post-Configuration Investigation:
  show isis adjacency          # See missing PE5 adjacencies
  show isis interface          # PE5 will show no ISIS interfaces
  show route protocol isis     # Routes via PE5 missing
  show system commit           # Trace deletion back to nilesh
  
Requirements:
  pip install junos-eznc
  
  Note: Run user_provisioning.py first to create nilesh user account.
        """
    )
    
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="🔍 Show what would be configured without applying (RECOMMENDED!)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="📊 Enable verbose output"
    )
    
    parser.add_argument(
        "--devices",
        type=str,
        help="🎯 Comma-separated list of specific devices to configure (e.g., pe1,pe2,pe3)"
    )
    
    args = parser.parse_args()
    
    # Parse device list if provided
    target_devices = None
    if args.devices:
        target_devices = [device.strip() for device in args.devices.split(',')]
    
    try:
        provisioner = UC4ISISProvisioning(
            dry_run=args.dry_run,
            verbose=args.verbose,
            target_devices=target_devices
        )
        
        provisioner.provision_all_devices()
        print("\n✅ Script 'isis_provisioning.py' completed successfully!\n")
        
    except KeyboardInterrupt:
        print("\n⚠️  ISIS provisioning interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ISIS provisioning failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

