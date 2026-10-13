// Read-only observation of the native detachable joint components. The stock
// plugin publishes only on transitions; repeat the measured state for reliable
// acknowledgement after transport delays, without creating or moving anything.
#include <gz/sim/System.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/components/DetachableJoint.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/components/ParentEntity.hh>
#include <gz/sim/components/Link.hh>
#include <gz/transport/Node.hh>
#include <gz/msgs/stringmsg.pb.h>
#include <gz/plugin/RegisterMore.hh>
#include <array>

namespace fieldlab {
class LatchMonitor: public gz::sim::System,
 public gz::sim::ISystemConfigure, public gz::sim::ISystemPostUpdate {
 gz::sim::Model carrier;
 gz::transport::Node node;
 std::array<gz::sim::Entity,8> parents{},children{};
 std::array<gz::transport::Node::Publisher,8> publishers;
 double last=-1;
 public:
 void Configure(const gz::sim::Entity &entity,
  const std::shared_ptr<const sdf::Element> &,
  gz::sim::EntityComponentManager &ecm,gz::sim::EventManager &) override {
  carrier=gz::sim::Model(entity);
  for(int i=0;i<8;++i){
   const std::string id="uav0"+std::to_string(i+1);
   parents[i]=carrier.LinkByName(ecm,"tray_"+id);
   publishers[i]=node.Advertise<gz::msgs::StringMsg>("/fieldlab/trays/"+id+"/latch_measured");
  }
 }
 void PostUpdate(const gz::sim::UpdateInfo &info,
  const gz::sim::EntityComponentManager &ecm) override {
  const double now=std::chrono::duration<double>(info.simTime).count();
  if(info.paused || now-last<.2)return;
  last=now;
  for(int i=0;i<8;++i)if(children[i]==gz::sim::kNullEntity){
   const auto model=ecm.EntityByComponents(gz::sim::components::Model(),
    gz::sim::components::Name("uav0"+std::to_string(i+1)));
   if(model!=gz::sim::kNullEntity)children[i]=gz::sim::Model(model).LinkByName(ecm,"base_link");
  }
  std::array<bool,8> attached{};
  ecm.Each<gz::sim::components::DetachableJoint>([&](const gz::sim::Entity &,
   const gz::sim::components::DetachableJoint *joint){
   for(int i=0;i<8;++i)if(joint->Data().parentLink==parents[i] &&
     joint->Data().childLink==children[i])attached[i]=true;
   return true;
  });
  for(int i=0;i<8;++i)if(children[i]!=gz::sim::kNullEntity){
   gz::msgs::StringMsg message;
   message.set_data(attached[i]?"attached":"detached");
   publishers[i].Publish(message);
  }
 }
};
}
GZ_ADD_PLUGIN(fieldlab::LatchMonitor,gz::sim::System,fieldlab::LatchMonitor::ISystemConfigure,fieldlab::LatchMonitor::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(fieldlab::LatchMonitor,"fieldlab::LatchMonitor")
