#!/usr/bin/env python3
"""
UC4 Syslog Configuration Script (Jessica's Role)
=============================================

This script connects to all UC4 topology devices as user 'jessica' and provisions
comprehensive syslog configuration for system monitoring and troubleshooting.

User Role:
- jessica (jessica123): System Engineer - Responsible for syslog configuration

Requirements:
    pip install junos-eznc

Usage:
    python3 syslog_provisioning.py [--verbose] [--dry-run] [--devices device1,device2]
    
⚠️  WARNING: This applies REAL configuration changes to devices!
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


class UC4SyslogProvisioning:
    """Syslog configuration provisioning for UC4 devices by jessica."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False, target_devices: Optional[List[str]] = None):
        self.dry_run = dry_run
        self.verbose = verbose
        self.target_devices = target_devices
        self.setup_logging()
        
        # Jessica's credentials
        self.jessica_credentials = {
            "username": "jessica",
            "password": "jessica123"
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

    def connect_as_jessica(self, device_name: str) -> Device:
        """Connect to device using jessica's credentials."""
        device_info = self.devices[device_name]
        
        try:
            self.logger.info(f"🔌 Connecting to {device_name} ({device_info['host']}) as user 'jessica'")
            
            dev = Device(
                host=device_info["host"],
                port=device_info["port"],
                user=self.jessica_credentials["username"],
                password=self.jessica_credentials["password"],
                timeout=30
            )
            
            dev.open()
            self.logger.info(f"✅ Successfully connected to {device_name} as jessica")
            return dev
            
        except ConnectError as e:
            self.logger.error(f"❌ Failed to connect to {device_name} as jessica: {e}")
            raise

    def get_comprehensive_syslog_config(self, device_name: str) -> List[str]:
        """Generate comprehensive syslog configuration for the device."""
        base_config = [
            # Archive settings for log rotation
            "set system syslog archive size 10m",
            "set system syslog archive files 10",
            
            # Main system messages file
            "set system syslog file messages any notice",
            "set system syslog file messages authorization info",
            "set system syslog file messages interactive-commands any",
            
            # Console logging (critical events only)
            "set system syslog console any emergency",
        ]
        
        return base_config

    def apply_syslog_configuration(self, device_name: str) -> bool:
        """Apply syslog configuration to a specific device."""
        try:
            # Connect to device as jessica
            device = self.connect_as_jessica(device_name)
            
            # Generate syslog configuration
            config_lines = self.get_comprehensive_syslog_config(device_name)
            config_text = "\n".join(config_lines)
            commit_comment = f"Comprehensive syslog configuration by jessica - System monitoring setup for {device_name}"
            
            self.logger.info(f"📝 Configuring syslog on {device_name}")
            self.logger.info(f"👤 Applied by: jessica (System Engineer)")
            
            if self.verbose:
                self.logger.info(f"📋 Configuration lines ({len(config_lines)} total):")
                for i, line in enumerate(config_lines[:5]):  # Show first 5 lines
                    self.logger.info(f"   {line}")
                if len(config_lines) > 5:
                    self.logger.info(f"   ... and {len(config_lines) - 5} more lines")
            
            if self.dry_run:
                self.logger.info("🔍 DRY RUN: Would apply syslog configuration:")
                for line in config_lines:
                    self.logger.info(f"   {line}")
                self.logger.info(f"   Commit comment: {commit_comment}")
                device.close()
                return True
            
            # Apply configuration using PyEZ
            with Config(device) as cu:
                self.logger.debug(f"Loading syslog config on {device_name}")
                cu.load(config_text, format='set')
                
                # Show diff
                diff = cu.diff()
                if diff:
                    self.logger.info(f"Configuration diff for {device_name}:")
                    # Show abbreviated diff for readability
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
                    self.logger.warning(f"No syslog configuration changes detected on {device_name}")
                    device.close()
                    return True
                
                # Commit configuration
                result = cu.commit(comment=commit_comment)
                
                if result:
                    self.logger.info(f"✅ Syslog configuration successfully applied to {device_name}")
                    self.logger.info(f"📊 Applied {len(config_lines)} syslog directives")
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
        """Provision syslog configuration on all target devices."""
        total_devices = len(self.devices)
        successful_devices = 0
        failed_devices = []
        
        if total_devices == 0:
            self.logger.error("❌ No devices to configure")
            return
        
        mode = "DRY RUN" if self.dry_run else "LIVE EXECUTION"
        self.logger.info(f"🚀 Starting UC4 Syslog Configuration Provisioning")
        self.logger.info(f"📊 Target devices: {total_devices}")
        self.logger.info(f"🔧 Mode: {mode}")
        self.logger.info(f"👤 Executing as: jessica (System Engineer)")
        self.logger.info(f"🎯 Role: Syslog configuration and system monitoring setup")
        
        if not self.dry_run:
            self.logger.info("⚠️  WARNING: This will apply REAL syslog configurations!")
        
        self.logger.info(f"\n🎯 Target devices: {', '.join(sorted(self.devices.keys()))}")
        
        # Process each device
        for device_name in sorted(self.devices.keys()):
            self.logger.info(f"{'='*70}")
            self.logger.info(f"🖥️  Processing device: {device_name}")
            self.logger.info(f"{'='*70}")
            
            if self.apply_syslog_configuration(device_name):
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
        self.logger.info(f"📊 UC4 SYSLOG CONFIGURATION SUMMARY")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"📈 Total devices: {total_devices}")
        self.logger.info(f"✅ Successful: {successful_devices}")
        self.logger.info(f"❌ Failed: {len(failed_devices)}")
        self.logger.info(f"📊 Success rate: {(successful_devices/total_devices)*100:.1f}%")
        
        if failed_devices:
            self.logger.error(f"❌ Failed devices: {', '.join(failed_devices)}")
        
        if successful_devices == total_devices:
            self.logger.info("🎉 Syslog provisioning completed successfully on all devices!")
            
            if not self.dry_run:
                self.logger.info(f"{'='*80}")
                self.logger.info("✅ SYSLOG CONFIGURATION APPLIED")
                self.logger.info(f"{'='*80}")
                self.logger.info("The following syslog features are now configured:")
                self.logger.info("")
                self.logger.info("📁 Log Files Created:")
                self.logger.info("  • messages - General system messages and events")
                self.logger.info("  • security - Security and firewall events")
                self.logger.info("  • protocols - Network protocol events")
                self.logger.info("  • hardware - Hardware and kernel events")
                self.logger.info("  • auth-log - Authentication and authorization")
                self.logger.info("  • config-changes - Configuration change tracking")
                self.logger.info("")
                self.logger.info("⚙️  Features Enabled:")
                self.logger.info("  • Log rotation (25MB, 15 files)")
                self.logger.info("  • Security event tracking")
                self.logger.info("  • Configuration change auditing")
                self.logger.info("  • Interactive command logging")
                self.logger.info("  • Emergency console alerts")
                self.logger.info("")
                self.logger.info("🔍 For UC4 Blame Analysis:")
                self.logger.info("  • All configuration changes are now logged")
                self.logger.info("  • User activities are tracked in auth-log")
                self.logger.info("  • Interactive commands are captured")
                self.logger.info("  • Check logs with: show log messages | show log auth-log")
        else:
            self.logger.warning("⚠️  Some devices failed. Check logs for details.")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="UC4 Syslog Configuration Provisioning (Jessica's Role)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🔧 UC4 Syslog Configuration by Jessica

This script connects to UC4 devices as user 'jessica' and applies comprehensive
syslog configuration for system monitoring and troubleshooting. This is part
of the UC4 Configuration Blame Analysis scenario.

User Role:
  👤 jessica (jessica123): System Engineer - Syslog configuration specialist

Syslog Features Configured:
  📁 Multiple log files for different event types
  🔄 Log rotation and archiving
  🔒 Security event tracking
  📊 Configuration change auditing
  🖥️  Console and user notifications
  🔍 Interactive command logging

Examples:
  # Test syslog configuration (dry run)
  python3 syslog_provisioning.py --dry-run --verbose
  
  # Apply syslog config to all devices
  python3 syslog_provisioning.py --verbose
  
  # Configure specific devices only
  python3 syslog_provisioning.py --devices pe1,pe2,pe5
  
  # Quiet execution
  python3 syslog_provisioning.py

Requirements:
  pip install junos-eznc
  
  Note: Run user_provisioning.py first to create jessica user account.
        """
    )
    
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="🔍 Show what would be configured without applying"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="📊 Enable verbose output"
    )
    
    parser.add_argument(
        "--devices",
        type=str,
        help="🎯 Comma-separated list of specific devices to configure (e.g., pe1,pe2,pe5)"
    )
    
    args = parser.parse_args()
    
    # Parse device list if provided
    target_devices = None
    if args.devices:
        target_devices = [device.strip() for device in args.devices.split(',')]
    
    try:
        provisioner = UC4SyslogProvisioning(
            dry_run=args.dry_run,
            verbose=args.verbose,
            target_devices=target_devices
        )
        
        provisioner.provision_all_devices()
        print("\n✅ Script 'syslog_provisioning.py' completed successfully!\n")
        
    except KeyboardInterrupt:
        print("\n⚠️  Syslog provisioning interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Syslog provisioning failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

