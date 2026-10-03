"""Single-SITL boundary tests; require the pinned px4_msgs overlay."""
import math
import time
import unittest
from unittest.mock import patch
import rclpy
from px4_msgs.msg import VehicleLocalPosition, VehicleStatus, VehicleLandDetected, VehicleCommand, VehicleCommandAck
from wildlife_interfaces.msg import DroneCommand, DroneState
from wildlife_simulation.px4_uav_adapter import PX4UAVAdapter, enu_to_ned, ned_to_enu, versioned_topic

class Capture:
    def __init__(self): self.messages=[]
    def publish(self,msg): self.messages.append(msg)

class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): rclpy.init(args=['--ros-args','-p','sitl_enabled:=true'])
    @classmethod
    def tearDownClass(cls): rclpy.shutdown()
    def setUp(self):
        self.n=PX4UAVAdapter()
        for attr in ('command_pub','heartbeat_pub','setpoint_pub','state_pub'):
            setattr(self.n,attr,Capture())
        self.n.status_cb(VehicleStatus(pre_flight_checks_pass=True, arming_state=VehicleStatus.ARMING_STATE_DISARMED))
        self.n.land_cb(VehicleLandDetected(landed=True))
        self.n.local_cb(VehicleLocalPosition(xy_valid=True,z_valid=True,x=2.,y=3.,z=-4.,heading=0.))
    def tearDown(self): self.n.destroy_node()
    def test_frame_conversion_and_versioned_topics(self):
        self.assertEqual(enu_to_ned((1,2,3)),[2.,1.,-3.])
        self.assertEqual(ned_to_enu(enu_to_ned((1,2,3))),(1.,2.,3.))
        self.assertEqual(versioned_topic('', 'out', 'vehicle_status',VehicleStatus),'/fmu/out/vehicle_status_v1')
    def test_telemetry_is_only_position_authority(self):
        n=self.n
        n.move_toward(5.,6.,10.)
        self.assertEqual((n.x,n.y,n.z),(3.,2.,4.))
        n.publish()
        p=n.state_pub.messages[-1].pose.pose.position
        self.assertEqual((p.x,p.y,p.z),(3.,2.,4.))
        self.assertEqual(n.state_pub.messages[-1].header.frame_id,'map')
    def test_invalid_position_rejects_commands(self):
        n=self.n
        n.local_cb(VehicleLocalPosition(xy_valid=False,z_valid=True))
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.LAUNCH))
        self.assertEqual(n.state,DroneState.STORED)
        n.tick()
        self.assertFalse(n.heartbeat_pub.messages)
    def test_prestream_before_offboard_or_arm(self):
        n=self.n
        n.command_cb(DroneCommand(drone_id=n.id,command=DroneCommand.LAUNCH))
        n.tick()
        self.assertEqual(n.state,DroneState.TAKEOFF)
        self.assertTrue(n.heartbeat_pub.messages)
        self.assertFalse(n.command_pub.messages)
        n.stream_start=time.monotonic()-2
        n.tick()
        self.assertEqual(n.command_pub.messages[-1].command,VehicleCommand.VEHICLE_CMD_DO_SET_MODE)
    def test_stale_telemetry_stops_heartbeat(self):
        n=self.n
        n.stream_start=time.monotonic()-2
        n.received['local']=time.monotonic()-10
        n.tick()
        self.assertIsNotNone(n.fault)
        self.assertFalse(n.heartbeat_pub.messages)
    def test_origin_reset_faults_after_takeoff(self):
        n=self.n;n.was_airborne=True
        n.local_cb(VehicleLocalPosition(xy_valid=True,z_valid=True,xy_reset_counter=1))
        self.assertIsNotNone(n.fault)
    def test_rejected_command_and_bounds_fault(self):
        n=self.n
        n.send_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE,1.,6.)
        n.ack_cb(VehicleCommandAck(command=VehicleCommand.VEHICLE_CMD_DO_SET_MODE,result=VehicleCommandAck.VEHICLE_CMD_RESULT_DENIED))
        self.assertIsNotNone(n.fault)
        self.assertFalse(n.move_toward(1000.,0.,10.))
    def test_return_uses_px4_rtl_and_measured_landing(self):
        n=self.n;n.state=DroneState.RETURNING;n.was_airborne=True
        n.land_cb(VehicleLandDetected(landed=False))
        n.status_cb(VehicleStatus(arming_state=VehicleStatus.ARMING_STATE_ARMED))
        n.tick()
        self.assertEqual(n.command_pub.messages[-1].command,VehicleCommand.VEHICLE_CMD_NAV_RETURN_TO_LAUNCH)
        self.assertNotEqual(n.state,DroneState.DOCKED)
        n.land_cb(VehicleLandDetected(landed=True))
        n.status_cb(VehicleStatus(arming_state=VehicleStatus.ARMING_STATE_DISARMED))
        n.tick()
        self.assertEqual(n.state,DroneState.DOCKED)

if __name__=='__main__':unittest.main()
