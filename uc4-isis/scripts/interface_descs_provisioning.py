#!/usr/bin/env python3
"""
UC4 Interface Description Configuration Script (Josemi's Role)
==========================================================

This script connects to all UC4 topology devices as user 'josemi' and provisions
interface descriptions based on the current network topology connections.

User Role:
- josemi (josemi123): Network Engineer - Responsible for interface descriptions

Requirements:
    pip install junos-eznc

Usage:
    python3 interface_provisioning.py [--verbose] [--dry-run] [--devices device1,device2]
    
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


class UC4InterfaceProvisioning:
    """Interface description provisioning for UC4 devices by josemi."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False, target_devices: Optional[List[str]] = None):
        self.dry_run = dry_run
        self.verbose = verbose
        self.target_devices = target_devices
        self.setup_logging()
        
        # Josemi's credentials
        self.josemi_credentials = {
            "username": "josemi",
            "password": "josemi123"
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
        
        # Interface descriptions gathered from current network topology
        self.interface_descriptions = {
            'pe1': {
                'eth1': 'PE1 eth1 <-> PE3 eth1',
                'eth2': 'PE1 eth2 <-> PE4 eth2', 
                'eth3': 'PE1 eth3 <-> PE2 eth3',
                'eth4': 'PE1 eth4 <-> PE2 eth4',
                'lo0': 'PE1 Loopback Interface'
            },
            'pe2': {
                'eth1': 'PE2 eth1 <-> PE4 eth1',
                'eth2': 'PE2 eth2 <-> PE3 eth2',
                'eth3': 'PE2 eth3 <-> PE1 eth3', 
                'eth4': 'PE2 eth4 <-> PE1 eth4',
                'lo0': 'PE2 Loopback Interface'
            },
            'pe3': {
                'eth1': 'PE3 eth1 <-> PE1 eth1',
                'eth2': 'PE3 eth2 <-> PE2 eth2',
                'eth3': 'PE3 eth3 <-> PE5 eth3',
                'eth4': 'PE3 eth4 <-> PE6 eth2',
                'eth5': 'PE3 eth5 <-> PE4 eth5',
                'lo0': 'PE3 Loopback Interface'
            },
            'pe4': {
                'eth1': 'PE4 eth1 <-> PE2 eth1',
                'eth2': 'PE4 eth2 <-> PE1 eth2',
                'eth3': 'PE4 eth3 <-> PE6 eth3',
                'eth4': 'PE4 eth4 <-> PE5 eth2',
                'eth5': 'PE4 eth5 <-> PE3 eth5',
                'lo0': 'PE4 Loopback Interface'
            },
            'pe5': {
                'eth1': 'PE5 eth1 <-> PE6 eth1',
                'eth2': 'PE5 eth2 <-> PE4 eth4',
                'eth3': 'PE5 eth3 <-> PE3 eth3',
                'lo0': 'PE5 Loopback Interface'
            },
            'pe6': {
                'eth1': 'PE6 eth1 <-> PE5 eth1',
                'eth2': 'PE6 eth2 <-> PE3 eth4',
                'eth3': 'PE6 eth3 <-> PE4 eth3',
                'lo0': 'PE6 Loopback Interface'
            }
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

    def connect_as_josemi(self, device_name: str) -> Device:
        """Connect to device using josemi's credentials."""
        device_info = self.devices[device_name]
        
        try:
            self.logger.info(f"🔌 Connecting to {device_name} ({device_info['host']}) as user 'josemi'")
            
            dev = Device(
                host=device_info["host"],
                port=device_info["port"],
                user=self.josemi_credentials["username"],
                password=self.josemi_credentials["password"],
                timeout=30
            )
            
            dev.open()
            self.logger.info(f"✅ Successfully connected to {device_name} as josemi")
            return dev
            
        except ConnectError as e:
            self.logger.error(f"❌ Failed to connect to {device_name} as josemi: {e}")
            raise

    def get_interface_descriptions_config(self, device_name: str) -> List[str]:
        """Generate interface description configuration for the device."""
        if device_name not in self.interface_descriptions:
            self.logger.warning(f"⚠️  No interface descriptions defined for {device_name}")
            return []
        
        config_lines = []
        device_interfaces = self.interface_descriptions[device_name]
        
        for interface, description in device_interfaces.items():
            config_lines.append(f"set interfaces {interface} unit 0 description \"{description}\"")
        
        return config_lines

    def check_existing_descriptions(self, device: Device, device_name: str) -> Dict[str, str]:
        """Check existing interface descriptions on the device."""
        try:
            # Get current interface configuration
            interfaces_config = device.rpc.get_configuration(filter_xml='<s><interfaces/></s>')
            existing_descriptions = {}
            
            for interface in interfaces_config.findall('.//interface'):
                interface_name = interface.find('name')
                if interface_name is not None:
                    for unit in interface.findall('.//unit'):
                        unit_name = unit.find('name')
                        description = unit.find('description')
                        if unit_name is not None and unit_name.text == '0' and description is not None:
                            existing_descriptions[interface_name.text] = description.text
            
            self.logger.debug(f"Existing descriptions on {device_name}: {existing_descriptions}")
            return existing_descriptions
            
        except Exception as e:
            self.logger.error(f"❌ Failed to check existing descriptions on {device_name}: {e}")
            return {}

    def apply_interface_descriptions(self, device_name: str) -> bool:
        """Apply interface descriptions to a specific device."""
        try:
            # Connect to device as josemi
            device = self.connect_as_josemi(device_name)
            
            # Check existing descriptions
            existing_descriptions = self.check_existing_descriptions(device, device_name)
            
            # Generate interface description configuration
            config_lines = self.get_interface_descriptions_config(device_name)
            
            if not config_lines:
                self.logger.warning(f"⚠️  No interface descriptions to configure on {device_name}")
                device.close()
                return True
            
            # Determine which descriptions need to be updated
            target_descriptions = self.interface_descriptions.get(device_name, {})
            descriptions_to_update = []
            unchanged_descriptions = []
            
            for interface, new_description in target_descriptions.items():
                existing_desc = existing_descriptions.get(interface)
                if existing_desc != new_description:
                    descriptions_to_update.append(interface)
                else:
                    unchanged_descriptions.append(interface)
            
            if unchanged_descriptions and self.verbose:
                self.logger.info(f"📌 Descriptions already correct on {device_name}: {', '.join(unchanged_descriptions)}")
            
            if not descriptions_to_update:
                self.logger.info(f"✅ All interface descriptions already configured correctly on {device_name}")
                device.close()
                return True
            
            # Filter config lines to only include interfaces that need updates
            filtered_config_lines = []
            for line in config_lines:
                for interface in descriptions_to_update:
                    if f"interfaces {interface} " in line:
                        filtered_config_lines.append(line)
                        break
            
            config_text = "\n".join(filtered_config_lines)
            commit_comment = f"Interface descriptions configured by josemi - Network topology documentation for {device_name}"
            
            self.logger.info(f"📝 Configuring interface descriptions on {device_name}")
            self.logger.info(f"👤 Applied by: josemi (Network Engineer)")
            self.logger.info(f"🔧 Updating descriptions for: {', '.join(descriptions_to_update)}")
            
            if self.verbose:
                self.logger.info(f"📋 Configuration lines ({len(filtered_config_lines)} total):")
                for line in filtered_config_lines:
                    self.logger.info(f"   {line}")
            
            if self.dry_run:
                self.logger.info("🔍 DRY RUN: Would apply interface descriptions:")
                for line in filtered_config_lines:
                    self.logger.info(f"   {line}")
                self.logger.info(f"   Commit comment: {commit_comment}")
                device.close()
                return True
            
            # Apply configuration using PyEZ
            with Config(device) as cu:
                self.logger.debug(f"Loading interface descriptions config on {device_name}")
                cu.load(config_text, format='set')
                
                # Show diff
                diff = cu.diff()
                if diff:
                    self.logger.info(f"Configuration diff for {device_name}:")
                    # Show abbreviated diff for readability
                    diff_lines = diff.split('\n')
                    if len(diff_lines) > 10 and not self.verbose:
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
                    self.logger.warning(f"No interface description changes detected on {device_name}")
                    device.close()
                    return True
                
                # Commit configuration
                result = cu.commit(comment=commit_comment)
                
                if result:
                    self.logger.info(f"✅ Interface descriptions successfully applied to {device_name}")
                    self.logger.info(f"📊 Updated {len(descriptions_to_update)} interface descriptions")
                    
                    # Show what was configured
                    if self.verbose:
                        self.logger.info(f"📝 Configured descriptions:")
                        for interface in descriptions_to_update:
                            desc = target_descriptions[interface]
                            self.logger.info(f"   {interface}: {desc}")
                    
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
        """Provision interface descriptions on all target devices."""
        total_devices = len(self.devices)
        successful_devices = 0
        failed_devices = []
        
        if total_devices == 0:
            self.logger.error("❌ No devices to configure")
            return
        
        mode = "DRY RUN" if self.dry_run else "LIVE EXECUTION"
        self.logger.info(f"🚀 Starting UC4 Interface Description Provisioning")
        self.logger.info(f"📊 Target devices: {total_devices}")
        self.logger.info(f"🔧 Mode: {mode}")
        self.logger.info(f"👤 Executing as: josemi (Network Engineer)")
        self.logger.info(f"🎯 Role: Interface description documentation")
        
        if not self.dry_run:
            self.logger.info("⚠️  WARNING: This will apply REAL interface configurations!")
        
        self.logger.info(f"\n🎯 Target devices: {', '.join(sorted(self.devices.keys()))}")
        
        # Show summary of interfaces to be configured
        total_interfaces = sum(len(self.interface_descriptions.get(device, {})) for device in self.devices.keys())
        self.logger.info(f"📝 Total interfaces to configure: {total_interfaces}")
        
        # Process each device
        for device_name in sorted(self.devices.keys()):
            self.logger.info(f"{'='*70}")
            self.logger.info(f"🖥️  Processing device: {device_name}")
            device_interfaces = self.interface_descriptions.get(device_name, {})
            self.logger.info(f"📝 Interfaces to configure: {len(device_interfaces)}")
            self.logger.info(f"{'='*70}")
            
            if self.apply_interface_descriptions(device_name):
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
        self.logger.info(f"📊 UC4 INTERFACE DESCRIPTION SUMMARY")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"📈 Total devices: {total_devices}")
        self.logger.info(f"✅ Successful: {successful_devices}")
        self.logger.info(f"❌ Failed: {len(failed_devices)}")
        self.logger.info(f"📊 Success rate: {(successful_devices/total_devices)*100:.1f}%")
        
        if failed_devices:
            self.logger.error(f"❌ Failed devices: {', '.join(failed_devices)}")
        
        if successful_devices == total_devices:
            self.logger.info("🎉 Interface description provisioning completed successfully!")
            
            if not self.dry_run:
                self.logger.info(f"{'='*80}")
                self.logger.info("✅ INTERFACE DESCRIPTIONS CONFIGURED")
                self.logger.info(f"{'='*80}")
                self.logger.info("Network topology documentation is now complete:")
                self.logger.info("")
                self.logger.info("📝 Configured Interface Types:")
                self.logger.info("  • Physical interfaces (eth1-eth5) - Point-to-point links")
                self.logger.info("  • Loopback interfaces (lo0) - Device identification")
                self.logger.info("")
                self.logger.info("🔗 Network Topology Links:")
                self.logger.info("  • PE1 ↔ PE2: 2 links (eth3, eth4)")
                self.logger.info("  • PE1 ↔ PE3: 1 link (eth1)")
                self.logger.info("  • PE1 ↔ PE4: 1 link (eth2)")
                self.logger.info("  • PE2 ↔ PE3: 1 link (eth2)")
                self.logger.info("  • PE2 ↔ PE4: 1 link (eth1)")
                self.logger.info("  • PE3 ↔ PE4: 1 link (eth5)")
                self.logger.info("  • PE3 ↔ PE5: 1 link (eth3)")
                self.logger.info("  • PE3 ↔ PE6: 1 link (eth4)")
                self.logger.info("  • PE4 ↔ PE5: 1 link (eth4)")
                self.logger.info("  • PE4 ↔ PE6: 1 link (eth3)")
                self.logger.info("  • PE5 ↔ PE6: 1 link (eth1)")
                self.logger.info("")
                self.logger.info("🔍 For UC4 Blame Analysis:")
                self.logger.info("  • All interface changes are now traceable to josemi")
                self.logger.info("  • Interface topology is documented and clear")
                # self.logger.info("  • Verify with: show interfaces descriptions") # Not running on cPRD :(
        else:
            self.logger.warning("⚠️  Some devices failed. Check logs for details.")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="UC4 Interface Description Provisioning (Josemi's Role)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🔧 UC4 Interface Description Configuration by Josemi

This script connects to UC4 devices as user 'josemi' and applies interface
descriptions based on the network topology. This is part of the UC4 
Configuration Blame Analysis scenario.

User Role:
  👤 josemi (josemi123): Network Engineer - Interface description specialist

Interface Documentation Features:
  📝 Physical interface descriptions (eth1-eth5)
  🔄 Loopback interface descriptions (lo0)
  🔗 Point-to-point link documentation
  📊 Network topology mapping
  🔍 Traceable configuration changes

Network Topology (11 total links):
  PE1 ↔ PE2: 2 links    PE3 ↔ PE5: 1 link
  PE1 ↔ PE3: 1 link     PE3 ↔ PE6: 1 link  
  PE1 ↔ PE4: 1 link     PE4 ↔ PE5: 1 link
  PE2 ↔ PE3: 1 link     PE4 ↔ PE6: 1 link
  PE2 ↔ PE4: 1 link     PE5 ↔ PE6: 1 link
  PE3 ↔ PE4: 1 link

Examples:
  # Test interface configuration (dry run)
  python3 interface_provisioning.py --dry-run --verbose
  
  # Apply interface descriptions to all devices
  python3 interface_provisioning.py --verbose
  
  # Configure specific devices only
  python3 interface_provisioning.py --devices pe1,pe2,pe3
  
  # Quiet execution
  python3 interface_provisioning.py

Requirements:
  pip install junos-eznc
  
  Note: Run user_provisioning.py first to create josemi user account.
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
        provisioner = UC4InterfaceProvisioning(
            dry_run=args.dry_run,
            verbose=args.verbose,
            target_devices=target_devices
        )
        
        provisioner.provision_all_devices()
        print("\n✅ Script 'interface_descs_provisioning.py' completed successfully!\n")
        
    except KeyboardInterrupt:
        print("\n⚠️  Interface provisioning interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Interface provisioning failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

