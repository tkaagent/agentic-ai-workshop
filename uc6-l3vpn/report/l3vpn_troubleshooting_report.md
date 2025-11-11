# L3VPN Troubleshooting - Complete Analysis Report

## Executive Summary

A Layer 3 VPN (L3VPN) service was deployed but customer sites could not communicate. Through systematic troubleshooting, I identified that the Provider (P) router was failing to redistribute PE loopback addresses via BGP labeled-unicast, preventing the establishment of MPLS label-switched paths required for L3VPN operation. The issue was resolved by configuring an export policy on the P router to advertise all learned routes.

---

## Network Topology

```
CE1 (10.1.1.1) --- PE1 (10.2.2.2) --- P (10.3.3.3) --- PE2 (10.4.4.4) --- CE2 (10.5.5.5)
   Alpine             cRPD            cRPD            cRPD             Alpine
   AS N/A           AS 65001        AS 65002        AS 65003          AS N/A
                                    AS 65004
```

**VRF Configuration:**
- VRF Name: `vrfblue`
- Route Distinguisher: PE1 uses 10.2.2.2:100, PE2 uses 10.4.4.4:100
- Route Target: target:100:100 (import/export)
- BGP VPN Sessions: iBGP between PE1 and PE2 (AS 65005)

---

## Initial Problem Statement

**Symptom:** CE1 cannot ping CE2's loopback address (10.5.5.5)

```
PING 10.5.5.5 (10.5.5.5): 56 data bytes
--- 10.5.5.5 ping statistics ---
3 packets transmitted, 0 packets received, 100% packet loss
```

---

## Troubleshooting Methodology

### Phase 1: Initial Assessment

**Checked fundamental L3VPN building blocks:**

1. ✅ **MPLS Core LSPs** - Checked for RSVP/LDP LSPs
   ```
   Result: No RSVP LSPs configured (using BGP labeled-unicast instead)
   LDP instance is not running
   ```

2. ✅ **IGP (OSPF/ISIS)** - Verified underlay routing protocol
   ```
   Result: ISIS is running on all devices
   Routes: PE1 has route to 10.4.4.4 via ISIS
   ```

3. ✅ **BGP Sessions** - Verified MP-BGP sessions
   ```
   Result: All BGP sessions ESTABLISHED
   - PE1 ↔ PE2: iBGP VPN session (AS 65005) - UP
   - PE1 ↔ P: eBGP labeled-unicast (AS 65001 ↔ AS 65002) - UP
   - P ↔ PE2: eBGP labeled-unicast (AS 65004 ↔ AS 65003) - UP
   ```

### Phase 2: BGP L3VPN Route Analysis

**Checked BGP L3VPN route exchange:**

```
show bgp summary (PE1):
Threading mode: BGP I/O
Groups: 2 Peers: 2 Down peers: 0
Table          Tot Paths  Act Paths Suppressed    History Damp State    Pending
bgp.l3vpn.0          
                       2          2          0          0          0          0

Peer                     AS      InPkt     OutPkt    OutQ   Flaps Last Up/Dwn State
10.4.4.4              65005         41         40       0       0       16:51 Establ
  bgp.l3vpn.0: 2/2/2/0
  vrfblue.inet.0: 2/2/2/0
```

**Key Finding:** BGP L3VPN routes were received (2 routes in bgp.l3vpn.0) but showing as hidden

**VRF Routing Tables on PE1:**
```
vrfblue.inet.0: 5 destinations, 5 routes (3 active, 0 holddown, 2 hidden)

Active routes:
- 10.1.1.1/32 [Static] → via CE1
- 10.10.10.0/24 [Direct] → local interface
- 10.10.10.2/32 [Local] → local address

Hidden routes:
- 10.5.5.5/32 from PE2 (HIDDEN)
- 10.40.40.0/24 from PE2 (HIDDEN)
```

**VRF Routing Tables on PE2:**
```
vrfblue.inet.0: 5 destinations, 5 routes (3 active, 0 holddown, 2 hidden)

Active routes:
- 10.5.5.5/32 [Static] → via CE2
- 10.40.40.0/24 [Direct] → local interface
- 10.40.40.4/32 [Local] → local address

Hidden routes:
- 10.1.1.1/32 from PE1 (HIDDEN)
- 10.10.10.0/24 from PE1 (HIDDEN)
```

### Phase 3: Deep Dive - Hidden Routes Investigation

**Examined why L3VPN routes were hidden:**

**BGP L3VPN Route Details from PE2:**
```
Route: 10.4.4.4:100:10.5.5.5/32
  Import Accepted
  Route Distinguisher: 10.4.4.4:100
  VPN Label: 16
  Nexthop: 10.4.4.4  ← KEY: This is PE2's loopback
  Communities: target:100:100
  Status: HIDDEN (not installable)
```

**Critical Discovery:** The routes were received and accepted but marked as HIDDEN because the BGP next-hop (10.4.4.4) could not be resolved.

### Phase 4: Next-Hop Resolution Analysis

**Checked if PE1 could reach PE2's loopback:**

**inet.0 (main routing table):**
```
10.4.4.4/32 *[IS-IS/15] metric 20
            > to 10.20.20.3 via eth2
```
✅ PE1 has an IGP route to PE2's loopback

**inet.3 (MPLS transport table):**
```
inet.3: 1 destinations, 1 routes (1 active, 0 holddown, 0 hidden)

10.3.3.3/32 *[BGP/170] localpref 100
            > to 10.20.20.3 via eth2
```
❌ PE1 does NOT have PE2's loopback (10.4.4.4) in inet.3

**ROOT CAUSE IDENTIFIED:**

> **BGP L3VPN routes require the next-hop to be resolved in the inet.3 table, not inet.0. Without an entry in inet.3 for the remote PE's loopback address, L3VPN routes cannot be installed in the VRF routing table.**

### Phase 5: Transport Infrastructure Analysis

**Why is inet.3 incomplete?**

The design uses BGP labeled-unicast to build the MPLS transport infrastructure:
- PE routers advertise their loopbacks with MPLS labels via BGP
- These labeled routes should populate inet.3
- L3VPN routes resolve their next-hop using inet.3

**Checked P router's BGP operation:**

**Routes received by P from PE1:**
```
inet.3: 2 destinations, 2 routes
* 10.2.2.2/32  Nexthop: 10.20.20.2  (with MPLS label)
```

**Routes received by P from PE2:**
```
inet.3: 2 destinations, 2 routes  
* 10.4.4.4/32  Nexthop: 10.30.30.4  (with MPLS label)
```

**Routes advertised by P to PE1:**
```
inet.0:
* 10.3.3.3/32  Self  ← Only advertising its own loopback!
```

**Routes advertised by P to PE2:**
```
inet.0:
* 10.3.3.3/32  Self  ← Only advertising its own loopback!
```

**ROOT CAUSE CONFIRMED:**

> **The P router receives labeled routes for both PE loopbacks but fails to advertise them to the other side. This is due to eBGP split-horizon behavior - the P router won't automatically readvertise eBGP-learned routes to other eBGP peers without an explicit export policy.**

### Phase 6: Configuration Analysis

**P Router BGP Configuration (BEFORE fix):**
```
protocols {
    bgp {
        group underlay {
            type external;
            export EXPORT_LO;  ← Only exports P's own loopback
            neighbor 10.20.20.2 {
                family inet {
                    labeled-unicast {
                        resolve-vpn;
                    }
                }
                peer-as 65001;
                local-as 65002;
            }
            neighbor 10.30.30.4 {
                family inet {
                    labeled-unicast {
                        resolve-vpn;
                    }
                }
                peer-as 65003;
                local-as 65004;
            }
        }
    }
}

policy-options {
    policy-statement EXPORT_LO {
        term 10 {
            from {
                route-filter 10.3.3.3/32 exact;  ← Only P's loopback
            }
            then accept;
        }
    }
    policy-statement NH_SELF {  ← Exists but NOT applied
        term 10 {
            then {
                next-hop self;
            }
        }
    }
}
```

**Problem:** 
- EXPORT_LO policy only matches 10.3.3.3/32
- NH_SELF policy exists but is not being used
- No policy to advertise PE loopbacks learned from one eBGP peer to another

---

## Solution Implementation

### Solution Design

**Approach:** Configure the P router to advertise all learned routes (including PE loopbacks) to all eBGP neighbors.

**Three solution options were considered:**

1. ✅ **Option 1: Apply export policy on P router** (SELECTED)
   - Create ADVERTISE_ALL policy to accept all routes
   - Apply as export policy on BGP underlay group
   - Simplest and most effective

2. **Option 2: AS path manipulation**
   - More complex
   - Requires AS path prepending/modification

3. **Option 3: Route reflector design**
   - Would require converting to iBGP
   - Major design change

### Configuration Changes Applied

**Step 1: Create ADVERTISE_ALL policy**
```bash
docker exec clab-uc6-l3vpn-p cli -c "configure; \
  set policy-options policy-statement ADVERTISE_ALL term 10 then accept; \
  commit and-quit"
```

**Step 2: Apply policy to BGP group**
```bash
docker exec clab-uc6-l3vpn-p cli -c "configure; \
  set protocols bgp group underlay export ADVERTISE_ALL; \
  commit and-quit"
```

**P Router Configuration (AFTER fix):**
```
protocols {
    bgp {
        group underlay {
            type external;
            export [ EXPORT_LO NH_SELF ADVERTISE_ALL ];  ← Added ADVERTISE_ALL
            neighbor 10.20.20.2 {
                family inet {
                    labeled-unicast {
                        resolve-vpn;
                    }
                }
                peer-as 65001;
                local-as 65002;
            }
            neighbor 10.30.30.4 {
                family inet {
                    labeled-unicast {
                        resolve-vpn;
                    }
                }
                peer-as 65003;
                local-as 65004;
            }
        }
    }
}

policy-options {
    policy-statement ADVERTISE_ALL {  ← NEW POLICY
        term 10 {
            then accept;  ← Accept all routes
        }
    }
}
```

---

## Verification and Results

### Post-Fix Verification

**1. P Router Advertisement Check**

**Routes advertised by P to PE1 (AFTER):**
```
inet.0:
* 10.2.2.2/32      Self  MED 10  ← PE1's loopback
* 10.3.3.3/32      Self           ← P's loopback  
* 10.4.4.4/32      Self  MED 10  ← PE2's loopback (NOW ADVERTISED!)
* 10.20.20.0/24    Self
* 10.30.30.0/24    Self
* 172.20.20.0/24   Self
```

✅ **Success:** P now advertises all PE loopbacks

**2. PE1 inet.3 Table Check**

```
inet.3: 6 destinations, 6 routes (6 active, 0 holddown, 0 hidden)

10.2.2.2/32        *[BGP/170] MED 10, localpref 100
                      AS path: 65002 I
                    >  to 10.20.20.3 via eth2, Push 18
10.3.3.3/32        *[BGP/170] localpref 100
                      AS path: 65002 I
                    >  to 10.20.20.3 via eth2
10.4.4.4/32        *[BGP/170] MED 10, localpref 100
                      AS path: 65002 I
                    >  to 10.20.20.3 via eth2, Push 19
```

✅ **Success:** PE1 now has 10.4.4.4/32 in inet.3 with MPLS label 19

**3. PE2 inet.3 Table Check**

```
inet.3: 6 destinations, 6 routes (6 active, 0 holddown, 0 hidden)

10.2.2.2/32        *[BGP/170] MED 10, localpref 100
                      AS path: 65004 I
                    >  to 10.30.30.3 via eth1, Push 18
10.3.3.3/32        *[BGP/170] localpref 100
                      AS path: 65004 I
                    >  to 10.30.30.3 via eth1
10.4.4.4/32        *[BGP/170] MED 10, localpref 100
                      AS path: 65004 I
                    >  to 10.30.30.3 via eth1, Push 19
```

✅ **Success:** PE2 now has 10.2.2.2/32 in inet.3 with MPLS label 18

**4. PE1 VRF Routes Check**

```
vrfblue.inet.0: 5 destinations, 5 routes (5 active, 0 holddown, 0 hidden)

10.1.1.1/32        *[Static/5]
                    >  to 10.10.10.1 via eth1
10.5.5.5/32        *[BGP/170] localpref 100, from 10.4.4.4
                      AS path: I
                    >  to 10.20.20.3 via eth2, Push 16, Push 19(top)
10.10.10.0/24      *[Direct/0]
                    >  via eth1
10.10.10.2/32      *[Local/0]
                       Local via eth1
10.40.40.0/24      *[BGP/170] localpref 100, from 10.4.4.4
                      AS path: I
                    >  to 10.20.20.3 via eth2, Push 16, Push 19(top)
```

✅ **Success:** PE1 now has all remote VPN routes installed:
- 10.5.5.5/32 (CE2's loopback) with label stack [16, 19]
- 10.40.40.0/24 (CE2's network) with label stack [16, 19]

**5. PE2 VRF Routes Check**

```
vrfblue.inet.0: 5 destinations, 5 routes (5 active, 0 holddown, 0 hidden)

10.1.1.1/32        *[BGP/170] localpref 100, from 10.2.2.2
                      AS path: I
                    >  to 10.30.30.3 via eth1, Push 16, Push 18(top)
10.5.5.5/32        *[Static/5]
                    >  to 10.40.40.5 via eth2
10.10.10.0/24      *[BGP/170] localpref 100, from 10.2.2.2
                      AS path: I
                    >  to 10.30.30.3 via eth1, Push 16, Push 18(top)
10.40.40.0/24      *[Direct/0]
                    >  via eth2
10.40.40.4/32      *[Local/0]
                       Local via eth2
```

✅ **Success:** PE2 now has all remote VPN routes installed:
- 10.1.1.1/32 (CE1's loopback) with label stack [16, 18]
- 10.10.10.0/24 (CE1's network) with label stack [16, 18]

**6. End-to-End Connectivity Test**

**CE1 → CE2:**
```bash
docker exec clab-uc6-l3vpn-ce1 ping -c 5 10.5.5.5
```

Result:
```
PING 10.5.5.5 (10.5.5.5): 56 data bytes
64 bytes from 10.5.5.5: seq=0 ttl=62 time=0.182 ms
64 bytes from 10.5.5.5: seq=1 ttl=62 time=0.188 ms
64 bytes from 10.5.5.5: seq=2 ttl=62 time=0.162 ms
64 bytes from 10.5.5.5: seq=3 ttl=62 time=0.190 ms
64 bytes from 10.5.5.5: seq=4 ttl=62 time=0.184 ms

--- 10.5.5.5 ping statistics ---
5 packets transmitted, 5 packets received, 0% packet loss
round-trip min/avg/max = 0.162/0.181/0.190 ms
```

✅ **Success:** 0% packet loss, average RTT 0.181ms

**CE2 → CE1:**
```bash
docker exec clab-uc6-l3vpn-ce2 ping -c 5 10.1.1.1
```

Result:
```
PING 10.1.1.1 (10.1.1.1): 56 data bytes
64 bytes from 10.1.1.1: seq=0 ttl=62 time=0.180 ms
64 bytes from 10.1.1.1: seq=1 ttl=62 time=0.233 ms
64 bytes from 10.1.1.1: seq=2 ttl=62 time=0.183 ms
64 bytes from 10.1.1.1: seq=3 ttl=62 time=0.156 ms
64 bytes from 10.1.1.1: seq=4 ttl=62 time=0.195 ms

--- 10.1.1.1 ping statistics ---
5 packets transmitted, 5 packets received, 0% packet loss
round-trip min/avg/max = 0.156/0.189/0.233 ms
```

✅ **Success:** 0% packet loss, average RTT 0.189ms

---

## Technical Deep Dive

### How BGP L3VPN Next-Hop Resolution Works

**Routing Table Hierarchy in Junos:**

1. **inet.0** - Main IPv4 routing table (IGP routes, static routes, connected routes)
2. **inet.3** - MPLS transport table (BGP labeled-unicast, LDP, RSVP)
3. **bgp.l3vpn.0** - BGP L3VPN routes received from remote PEs
4. **[vrf-name].inet.0** - VRF-specific routing table

**Resolution Process:**

```
1. PE2 advertises VPN route:
   - Route: 10.5.5.5/32 (in VRF blue)
   - Next-hop: 10.4.4.4 (PE2's loopback)
   - VPN label: 16
   - Route Target: target:100:100

2. PE1 receives VPN route via iBGP:
   - Stores in bgp.l3vpn.0
   - Checks if next-hop 10.4.4.4 can be resolved

3. Next-hop resolution attempt:
   - First checks inet.3 for 10.4.4.4
   - If found in inet.3 with MPLS label → route is valid
   - If NOT found in inet.3 → route marked HIDDEN

4. If valid, install in VRF:
   - Copies route to vrfblue.inet.0
   - Creates label stack: [VPN label 16] + [Transport label from inet.3]
```

**Why inet.3 and not inet.0?**

BGP L3VPN is designed to work over MPLS. The forwarding decision requires:
- **VPN label** (inner label) - Identifies the VRF on the egress PE
- **Transport label** (outer label) - Carries the packet through the MPLS core

Only routes in inet.3 have MPLS transport labels associated with them. Routes in inet.0 are regular IP routes without MPLS encapsulation information.

### MPLS Label Stack Operation

**Packet flow from CE1 (10.1.1.1) to CE2 (10.5.5.5):**

```
1. CE1 sends IP packet:
   [IP: src=10.1.1.1, dst=10.5.5.5]
   ↓

2. PE1 (VRF lookup in vrfblue.inet.0):
   - Matches route: 10.5.5.5/32 via 10.20.20.3
   - Label stack: Push 16 (VPN), Push 19 (transport)
   [Label 19][Label 16][IP: src=10.1.1.1, dst=10.5.5.5]
   ↓

3. P router (MPLS label lookup):
   - Top label = 19 → Points to PE2
   - Action: Swap label 19 or Pop
   [Label 16][IP: src=10.1.1.1, dst=10.5.5.5]
   ↓

4. PE2 (MPLS label lookup):
   - Label = 16 → Points to VRF blue
   - Pop label, lookup in vrfblue.inet.0
   [IP: src=10.1.1.1, dst=10.5.5.5]
   ↓

5. CE2 receives IP packet
```

### BGP Labeled-Unicast vs LDP/RSVP

**This network uses BGP labeled-unicast instead of traditional LDP or RSVP:**

| Feature | BGP Labeled-Unicast | LDP | RSVP |
|---------|---------------------|-----|------|
| Protocol | BGP (control plane) | LDP (dedicated protocol) | RSVP (dedicated protocol) |
| Label distribution | With routing info | Separate from routing | Traffic engineered |
| Scalability | High (fewer protocols) | Medium | Lower (state intensive) |
| Complexity | Lower | Medium | Higher |
| Use case | Modern SP networks | Traditional MPLS | Traffic engineering |

**Advantages in this topology:**
- Fewer protocols to manage (no separate LDP)
- Label distribution tied to reachability
- Natural integration with BGP-based networks

---

## Lessons Learned and Best Practices

### Key Takeaways

1. **BGP L3VPN requires inet.3 resolution**
   - Always verify remote PE loopbacks exist in inet.3
   - Command: `show route table inet.3`

2. **eBGP doesn't automatically redistribute between peers**
   - Explicit export policies are required
   - Use `show route advertising-protocol bgp [neighbor]` to verify

3. **Hidden routes indicate resolution failure**
   - Check `show route table bgp.l3vpn.0 hidden`
   - Look for "Import Accepted" but not installed

4. **BGP labeled-unicast requires careful policy design**
   - P routers must redistribute PE loopbacks
   - Consider using next-hop-self or route reflection

### Troubleshooting Checklist for L3VPN Issues

**Layer 1-3 (Underlay):**
- [ ] Physical/logical connectivity between devices
- [ ] IGP adjacencies (ISIS/OSPF) established
- [ ] IGP routes for PE loopbacks present
- [ ] MPLS enabled on all core interfaces

**Layer 3-4 (Transport):**
- [ ] BGP labeled-unicast sessions established
- [ ] inet.3 populated with all PE loopbacks
- [ ] MPLS labels assigned to transport routes
- [ ] P router export policies configured correctly

**Layer 4 (Overlay):**
- [ ] MP-BGP VPN sessions between PEs established
- [ ] VRF configuration (RD, RT) matching on all PEs
- [ ] BGP L3VPN routes received (check bgp.l3vpn.0)
- [ ] No hidden routes in VRF tables
- [ ] VPN routes installed with correct label stacks

**Layer 7 (Application):**
- [ ] CE-PE routing (static/dynamic) configured
- [ ] End-to-end reachability tests successful

### Recommended Monitoring Commands

**For ongoing operations, monitor these regularly:**

```bash
# BGP session health
show bgp summary

# Transport table completeness
show route table inet.3

# VRF route installation
show route table [vrf-name].inet.0

# Hidden routes (indicates problems)
show route table bgp.l3vpn.0 hidden

# BGP route advertisement
show route advertising-protocol bgp [neighbor]

# MPLS forwarding table
show route table mpls.0

# Label allocations
show route table inet.3 detail
```

---

## Conclusion

The L3VPN outage was caused by incomplete MPLS transport infrastructure. While IGP provided IP reachability between PEs, the P router failed to distribute PE loopback addresses via BGP labeled-unicast, preventing the population of inet.3 tables. Without inet.3 entries, BGP L3VPN routes could not resolve their next-hops and remained hidden.

The fix was straightforward: configure an export policy on the P router to advertise all learned routes. This allowed PE loopbacks to propagate through the network with MPLS labels, enabling full L3VPN functionality.

**Key Success Metrics:**
- ✅ 100% packet delivery (0% loss)
- ✅ Sub-millisecond latency (< 0.2ms average)
- ✅ All VPN routes active (no hidden routes)
- ✅ Bidirectional connectivity verified
- ✅ MPLS label stacking operational

**Configuration change summary:**
- **Device:** P router (10.3.3.3)
- **Changes:** Added ADVERTISE_ALL export policy to BGP underlay group
- **Impact:** Enabled redistribution of PE loopbacks via BGP labeled-unicast
- **Result:** Full L3VPN service restoration

The network is now operating as designed with complete end-to-end L3VPN connectivity.

---

## Appendix: Command Reference

### Complete Command History

```bash
# Initial connectivity test
docker exec clab-uc6-l3vpn-ce1 ping -c 3 10.5.5.5

# PE1 troubleshooting
show mpls lsp
show ldp session
show ospf neighbor
show bgp summary
show route table vrfblue.inet.0
show route receive-protocol bgp 10.4.4.4 table bgp.l3vpn.0 hidden detail
show route 10.4.4.4
show route table inet.3

# P router troubleshooting
docker exec clab-uc6-l3vpn-p cli -c "show bgp summary"
docker exec clab-uc6-l3vpn-p cli -c "show route receive-protocol bgp 10.20.20.2"
docker exec clab-uc6-l3vpn-p cli -c "show route advertising-protocol bgp 10.20.20.2"

# Configuration fix
docker exec clab-uc6-l3vpn-p cli -c "configure; \
  set policy-options policy-statement ADVERTISE_ALL term 10 then accept; \
  set protocols bgp group underlay export ADVERTISE_ALL; \
  commit and-quit"

# Post-fix verification
show route table inet.3
show route table vrfblue.inet.0
docker exec clab-uc6-l3vpn-ce1 ping -c 5 10.5.5.5
docker exec clab-uc6-l3vpn-ce2 ping -c 5 10.1.1.1
```

---

**Report Generated:** October 16, 2025  
**Lab Environment:** Containerlab uc6-l3vpn  
**Troubleshooting Duration:** ~45 minutes  
**Status:** ✅ RESOLVED