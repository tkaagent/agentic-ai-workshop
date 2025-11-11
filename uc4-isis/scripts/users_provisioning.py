#!/usr/bin/env python3
"""
UC4 User Provisioning Script
============================

This script connects to all UC4 topology devices as user 'rami' and provisions
the other team users (josemi, jessica, nilesh) with their respective credentials.

User Credentials:
- rami/rami123: System Administrator (connects and creates other users)
- josemi/josemi123: Network Engineer (to be created for interface descriptions)
- jessica/jessica123: System Engineer (to be created for syslog configuration)
- nilesh/nilesh123: Routing Engineer (to be created for ISIS configuration)

Requirements:
    pip install junos-eznc

Usage:
    python3 user_provisioning.py [--verbose] [--dry-run]
"""

import argparse
import logging
import sys
from typing import Dict, List

# Import Juniper PyEZ
try:
    from jnpr.junos import Device
    from jnpr.junos.utils.config import Config
    from jnpr.junos.exception import ConnectError, ConfigLoadError, CommitError, LockError
except ImportError:
    print("❌ ERROR: PyEZ library not found.")
    print("Install with: pip install junos-eznc")
    sys.exit(1)


class UC4UserProvisioning:
    """User provisioning for UC4 Configuration Blame Analysis."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.setup_logging()
        
        # Rami's credentials for connecting to devices
        self.rami_credentials = {
            "username": "rami",
            "password": "rami123"
        }
        
        # Users to be created
        self.users_to_create = {
            "josemi": {
                "password": "josemi123",
                "uid": 2001,
                "class": "super-user",
                "role": "Network Engineer - Interface descriptions"
            },
            "jessica": {
                "password": "jessica123",
                "uid": 2002,
                "class": "super-user", 
                "role": "System Engineer - Syslog configuration"
            },
            "nilesh": {
                "password": "nilesh123",
                "uid": 2003,
                "class": "super-user",
                "role": "Routing Engineer - ISIS protocol"
            }
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

    def connect_as_rami(self, device_name: str) -> Device:
        """Connect to device using rami's credentials."""
        device_info = self.devices[device_name]
        
        try:
            self.logger.info(f"🔌 Connecting to {device_name} ({device_info['host']}) as user 'rami'")
            
            dev = Device(
                host=device_info["host"],
                port=device_info["port"],
                user=self.rami_credentials["username"],
                password=self.rami_credentials["password"],
                timeout=30
            )
            
            dev.open()
            self.logger.info(f"✅ Successfully connected to {device_name} as rami")
            return dev
            
        except ConnectError as e:
            self.logger.error(f"❌ Failed to connect to {device_name} as rami: {e}")
            raise

    def check_existing_users(self, device: Device, device_name: str) -> List[str]:
        """Check which users already exist on the device."""
        try:
            # Get current user configuration
            users_output = device.rpc.get_configuration(filter_xml='<s><login/></s>')
            existing_users = []
            
            for user in users_output.findall('.//user'):
                name = user.find('name')
                if name is not None:
                    existing_users.append(name.text)
            
            self.logger.debug(f"Existing users on {device_name}: {existing_users}")
            return existing_users
            
        except Exception as e:
            self.logger.error(f"❌ Failed to check existing users on {device_name}: {e}")
            return []

    def create_users_on_device(self, device_name: str) -> bool:
        """Create team users on a specific device."""
        try:
            # Connect to device as rami
            device = self.connect_as_rami(device_name)
            
            # Check existing users
            existing_users = self.check_existing_users(device, device_name)
            
            # Determine which users need to be created
            users_to_create = []
            for username in self.users_to_create:
                if username not in existing_users:
                    users_to_create.append(username)
                else:
                    self.logger.info(f"👤 User '{username}' already exists on {device_name}")
            
            if not users_to_create:
                self.logger.info(f"✅ All users already exist on {device_name}")
                device.close()
                return True
            
            # Generate configuration for users that need to be created
            config_lines = []
            for username in users_to_create:
                user_info = self.users_to_create[username]
                config_lines.extend([
                    f"set system login user {username} uid {user_info['uid']}",
                    f"set system login user {username} class {user_info['class']}",
                    f"set system login user {username} authentication plain-text-password-value {user_info['password']}"
                ])
            
            config_text = "\n".join(config_lines)
            commit_comment = f"Created team users: {', '.join(users_to_create)} [Provisioned by rami]"
            
            self.logger.info(f"📝 Creating users on {device_name}: {', '.join(users_to_create)}")
            
            if self.dry_run:
                self.logger.info("🔍 DRY RUN: Would create the following configuration:")
                for line in config_lines:
                    self.logger.info(f"   {line}")
                self.logger.info(f"   Commit comment: {commit_comment}")
                device.close()
                return True
            
            # Apply configuration
            with Config(device) as cu:
                self.logger.debug(f"Loading config:\n{config_text}")
                cu.load(config_text, format='set')
                
                # Show diff
                diff = cu.diff()
                if diff:
                    self.logger.info(f"Configuration diff:\n{diff}")
                else:
                    self.logger.warning("No configuration changes detected")
                    device.close()
                    return True
                
                # Commit configuration
                result = cu.commit(comment=commit_comment)
                
                if result:
                    self.logger.info(f"✅ Successfully created users on {device_name}: {', '.join(users_to_create)}")
                    
                    # Show created users with their roles
                    for username in users_to_create:
                        role = self.users_to_create[username]['role']
                        self.logger.info(f"   👤 {username}: {role}")
                    
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
        """Provision users on all UC4 devices."""
        total_devices = len(self.devices)
        successful_devices = 0
        failed_devices = []
        
        mode = "DRY RUN" if self.dry_run else "LIVE EXECUTION"
        self.logger.info(f"🚀 Starting UC4 User Provisioning")
        self.logger.info(f"📊 Target devices: {total_devices}")
        self.logger.info(f"🔧 Mode: {mode}")
        self.logger.info(f"👤 Connecting as: {self.rami_credentials['username']}")
        
        # Show users to be created
        self.logger.info(f"\n👥 Users to be provisioned:")
        for username, info in self.users_to_create.items():
            self.logger.info(f"   {username} ({info['password']}): {info['role']}")
        
        if not self.dry_run:
            self.logger.info("⚠️  WARNING: This will create REAL user accounts on devices!")
        
        self.logger.info(f"\n🎯 Processing devices:")
        
        # Process each device
        for device_name in sorted(self.devices.keys()):
            self.logger.info(f"{'='*60}")
            self.logger.info(f"🖥️  Processing device: {device_name}")
            self.logger.info(f"{'='*60}")
            
            if self.create_users_on_device(device_name):
                successful_devices += 1
                self.logger.info(f"✅ {device_name}: SUCCESS")
            else:
                failed_devices.append(device_name)
                self.logger.error(f"❌ {device_name}: FAILED")
        
        # Summary
        self.logger.info(f"{'='*80}")
        self.logger.info(f"📊 UC4 USER PROVISIONING SUMMARY")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"📈 Total devices: {total_devices}")
        self.logger.info(f"✅ Successful: {successful_devices}")
        self.logger.info(f"❌ Failed: {len(failed_devices)}")
        self.logger.info(f"📊 Success rate: {(successful_devices/total_devices)*100:.1f}%")
        
        if failed_devices:
            self.logger.error(f"❌ Failed devices: {', '.join(failed_devices)}")
        
        if successful_devices == total_devices:
            self.logger.info("🎉 User provisioning completed successfully on all devices!")
            
            if not self.dry_run:
                self.logger.info(f"{'='*80}")
                self.logger.info("✅ NEXT STEPS")
                self.logger.info(f"{'='*80}")
                self.logger.info("Users are now created and ready for UC4 blame analysis:")
                self.logger.info("")
                self.logger.info("1. josemi can now configure interface descriptions")
                self.logger.info("2. jessica can now configure syslog settings")
                self.logger.info("3. nilesh can now configure ISIS protocol")
                self.logger.info("")
                self.logger.info("Test user access:")
                self.logger.info("  ssh josemi@<device-ip>  # password: josemi123")
                self.logger.info("  ssh jessica@<device-ip> # password: jessica123") 
                self.logger.info("  ssh nilesh@<device-ip> # password: nilesh123")
        else:
            self.logger.warning("⚠️  Some devices failed. Check logs for details.")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="UC4 User Provisioning Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🔧 UC4 User Provisioning

This script connects to all UC4 topology devices as user 'rami' and creates
the team users (josemi, jessica, nilesh) required for configuration blame analysis.

User Roles:
  👤 rami (rami123): System Administrator - Creates other users
  👤 josemi (josemi123): Network Engineer - Interface descriptions  
  👤 jessica (jessica123): System Engineer - Syslog configuration
  👤 nilesh (nilesh123): Routing Engineer - ISIS protocol

Examples:
  # Test provisioning (dry run)
  python3 user_provisioning.py --dry-run --verbose
  
  # Execute real provisioning
  python3 user_provisioning.py --verbose
  
  # Quiet execution
  python3 user_provisioning.py

Requirements:
  pip install junos-eznc
        """
    )
    
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="🔍 Show what would be changed without applying"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="📊 Enable verbose output"
    )
    
    args = parser.parse_args()
    
    try:
        provisioner = UC4UserProvisioning(
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        provisioner.provision_all_devices()
        print("\n✅ Script 'users_provisioning.py' completed successfully!\n")
        
    except KeyboardInterrupt:
        print("\n⚠️  User provisioning interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ User provisioning failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

