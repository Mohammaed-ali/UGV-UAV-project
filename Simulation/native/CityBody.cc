// Background velocity control and procedural visual articulation.
// No pose resets or world-pose commands are used for normal city motion.
#include <gz/sim/System.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/Link.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/Pose.hh>
#include <gz/transport/Node.hh>
#include <gz/msgs/twist.pb.h>
#include <gz/msgs/pose_v.pb.h>
#include <gz/msgs/stringmsg.pb.h>
#include <gz/plugin/Register.hh>
#include <gz/common/Console.hh>
#include <mutex>
#include <cmath>
#include <vector>
#include <algorithm>

namespace fieldlab {
// Physical spacing is checked beside the bodies at the guidance rate. Python
// still owns traffic permissions; delayed callbacks cannot permit contact.
struct Occupant { gz::sim::Entity body; double length, width; };
static std::vector<Occupant> occupants;
static std::mutex occupantsMutex;
static bool rectanglesOverlap(const gz::math::Pose3d &a,double al,double aw,
                              const gz::math::Pose3d &b,double bl,double bw,double margin) {
  const double ay=a.Rot().Yaw(),by=b.Rot().Yaw();
  const gz::math::Vector3d ax(std::cos(ay),std::sin(ay),0),ayAxis(-std::sin(ay),std::cos(ay),0);
  const gz::math::Vector3d bx(std::cos(by),std::sin(by),0),byAxis(-std::sin(by),std::cos(by),0);
  const auto delta=b.Pos()-a.Pos();
  for(const auto &axis:{ax,ayAxis,bx,byAxis}) {
    const double extent=std::abs(axis.Dot(ax))*al/2.+std::abs(axis.Dot(ayAxis))*aw/2.
                       +std::abs(axis.Dot(bx))*bl/2.+std::abs(axis.Dot(byAxis))*bw/2.+margin;
    if(std::abs(delta.Dot(axis))>extent)return false;
  }
  return true;
}
class CityBody: public gz::sim::System,
                public gz::sim::ISystemConfigure,
                public gz::sim::ISystemPreUpdate {
  struct Part { std::string name, kind; gz::sim::Entity entity{}; gz::math::Vector3d pivot; double radius; bool steering; double wheelbase; };
  gz::sim::Model model;
  gz::sim::Link body;
  gz::transport::Node node;
  std::mutex mutex;
  double speed=0, turn=0, receivedAt=-10, simTime=0, travelled=0;
  gz::math::Vector3d previous;
  bool havePrevious=false; double previousYaw=0;
  std::vector<Part> parts;
  std::vector<gz::math::Vector3d> route,pendingRoute;bool routePending=false,ackPending=false;
  std::int64_t pendingVersion=0,activeVersion=0;gz::transport::Node::Publisher routeAck;
  double lookahead=2.,guidanceAt=-1.,guidedTurn=0.,guidedSpeed=0.,guidedCurvature=0.,previousProgress=0.;
  double safetyAt=-1.,safetyFactor=1.;
  bool haveProgress=false; double length=1.,width=.65,clearance=.65;
public:
  void Configure(const gz::sim::Entity &entity,
    const std::shared_ptr<const sdf::Element> &sdf,
    gz::sim::EntityComponentManager &ecm, gz::sim::EventManager &) override {
    model=gz::sim::Model(entity);
    body=gz::sim::Link(model.LinkByName(ecm,"body"));
    const auto footprint=sdf->Get<gz::math::Vector3d>("footprint",{1.,.65,0.}).first;
    length=footprint.X();width=footprint.Y();clearance=length<2. ? .65:.4;
    {std::lock_guard<std::mutex> guard(occupantsMutex);occupants.push_back({body.Entity(),length,width});}
    node.Subscribe<gz::msgs::Twist>("/fieldlab/city/"+model.Name(ecm)+"/cmd_vel",[this](const gz::msgs::Twist &msg){
      std::lock_guard<std::mutex> guard(mutex);
      speed=std::clamp(msg.linear().x(),0.,length<2. ? 5.:20.);
      turn=std::clamp(msg.angular().z(),-1.,1.);receivedAt=simTime;
    });
    routeAck=node.Advertise<gz::msgs::StringMsg>("/fieldlab/city/"+model.Name(ecm)+"/route_applied");
    node.Subscribe<gz::msgs::Pose_V>("/fieldlab/city/"+model.Name(ecm)+"/route",[this](const gz::msgs::Pose_V &msg){
      std::lock_guard<std::mutex> guard(mutex);pendingVersion=msg.header().stamp().sec();
      if(pendingVersion!=activeVersion){
        pendingRoute.clear();for(const auto &p:msg.pose())pendingRoute.emplace_back(p.position().x(),p.position().y(),0.);
        routePending=true;
      }
      ackPending=true;
    });
    // Keep the cloned parent alive: sibling traversal uses its parent link.
    const auto config=sdf->Clone();
    lookahead=sdf->Get<double>("lookahead",2.).first;
    if(sdf->HasElement("waypoint")){
      auto point=config->GetElement("waypoint");
      while(point){route.push_back(point->Get<gz::math::Vector3d>());point=point->GetNextElement("waypoint");}
    }
    gzmsg << model.Name(ecm) << " native path points: " << route.size() << std::endl;
    if(sdf->HasElement("part")) {
      auto element=config->GetElement("part");
      while(element) {
        parts.push_back({element->Get<std::string>("name"),element->Get<std::string>("kind"),
                         gz::sim::kNullEntity,element->Get<gz::math::Vector3d>("pivot"),element->Get<double>("radius",.35).first,element->Get<bool>("steering",false).first,element->Get<double>("wheelbase",3.2).first});
        element=element->GetNextElement("part");
      }
    }
  }
  void PreUpdate(const gz::sim::UpdateInfo &info, gz::sim::EntityComponentManager &ecm) override {
    if(info.paused || !body.Valid(ecm))return;
    double v,w;std::int64_t acknowledge=0;
    {
      std::lock_guard<std::mutex> guard(mutex);
      simTime=std::chrono::duration<double>(info.simTime).count();
      const bool fresh=simTime-receivedAt<.55;
      v=fresh?speed:0.;w=fresh?turn:0.;
      if(routePending){route=std::move(pendingRoute);routePending=false;activeVersion=pendingVersion;haveProgress=false;havePrevious=false;guidanceAt=-1.;safetyAt=-1.;}
      if(ackPending){acknowledge=activeVersion;ackPending=false;}
    }
    if(acknowledge){gz::msgs::StringMsg msg;msg.set_data(std::to_string(acknowledge));routeAck.Publish(msg);}
    const auto world=gz::sim::worldPose(body.Entity(),ecm);const auto current=world.Pos();
    if(havePrevious && (current-previous).Length()>2.){haveProgress=false;havePrevious=false;guidanceAt=-1.;safetyAt=-1.;}
    // Guidance stays beside physics so delayed Python pose callbacks cannot
    // steer actors using an old heading. Python retains speed, traffic and
    // crossing permissions; a stale command still stops the physical body.
    if(route.size()>1){
      if(simTime-guidanceAt>=.02){
        guidanceAt=simTime;double nearest=1e9,progress=0,total=0,best=0.;
        double routeLength=0.;for(size_t i=0;i+1<route.size();++i)routeLength+=(route[i+1]-route[i]).Length();
        std::vector<double> cumulative{0.};
        for(size_t i=0;i+1<route.size();++i){
          auto delta=route[i+1]-route[i];const double length=delta.Length();
          const double t=std::clamp((current-route[i]).Dot(delta)/std::max(1e-9,length*length),0.,1.);
          const double error=(current-route[i]-delta*t).Length();
          const double along=total+t*length;
          const bool continuous=!haveProgress || std::abs(std::remainder(along-previousProgress,std::max(.001,routeLength)))<12.;
          const double alignment=std::cos(std::atan2(delta.Y(),delta.X())-world.Rot().Yaw());
          // Direction breaks equal-distance ties on bidirectional crossings.
          const double cost=error+(!haveProgress ? (1.-alignment)*1e-5:0.);
          if(continuous && cost<nearest){nearest=cost;best=along;}
          total+=length;cumulative.push_back(total);
        }
        previousProgress=best;haveProgress=true;
        const double pursuit=std::max(lookahead,std::min(6.,v*.3));
        progress=std::fmod(best+pursuit,std::max(.001,total));
        auto goal=route.front();
        for(size_t i=0;i+1<route.size();++i)if(cumulative[i+1]>=progress){
          goal=route[i]+(route[i+1]-route[i])*((progress-cumulative[i])/std::max(1e-9,cumulative[i+1]-cumulative[i]));break;
        }
        const double error=std::remainder(std::atan2(goal.Y()-current.Y(),goal.X()-current.X())-world.Rot().Yaw(),2*M_PI);
        guidedTurn=std::clamp(error*2.5,-.8,.8);
        guidedCurvature=2.*std::sin(error)/std::max(.5,(goal-current).Length());
        guidedSpeed=nearest<1.4 ? std::max(0.,std::cos(error)):0.;
      }
      const bool fast=v>(length<2. ? 1.6:3.);
      v*=guidedSpeed;
      if(fast){const double curvature=std::max(.001,std::abs(guidedCurvature));v=std::min({v,std::sqrt(2.5/curvature),.7/curvature});}
      w=v>.001?(fast?std::clamp(v*guidedCurvature,-.8,.8):guidedTurn):0.;
    }
    // Check a short swept motion forecast with oriented rectangles. A broad
    // forward bounding corridor falsely blocks a turning bus beside parking.
    // Current physical poses and the current commanded twist are the only inputs.
    if(v>0. && simTime-safetyAt>=.02) {
      safetyAt=simTime;const double requested=v;
      std::vector<Occupant> peers;
      {std::lock_guard<std::mutex> guard(occupantsMutex);peers=occupants;}
      const double yaw=world.Rot().Yaw(),horizon=.8;
      for(const auto &peer:peers) {
        if(peer.body==body.Entity() || !ecm.HasEntity(peer.body))continue;
        const auto other=gz::sim::worldPose(peer.body,ecm);
        if((other.Pos()-current).Length()>std::hypot(length,width)/2.+std::hypot(peer.length,peer.width)/2.+v*horizon+clearance)continue;
        for(int step=1;step<=8;++step) {
          const double t=step*.1,angle=yaw+w*t;
          auto position=current;
          if(std::abs(w)>.001) {
            position.X()+=v*(std::sin(angle)-std::sin(yaw))/w;
            position.Y()+=v*(std::cos(yaw)-std::cos(angle))/w;
          } else {position.X()+=v*t*std::cos(yaw);position.Y()+=v*t*std::sin(yaw);}
          const gz::math::Pose3d predicted(position,gz::math::Quaterniond(0,0,angle));
          if(rectanglesOverlap(predicted,length,width,other,peer.length,peer.width,clearance)) {
            v*=std::max(0.,t-.1)/horizon;break;
          }
        }
      }
      safetyFactor=requested>0. ? v/requested:0.;
    } else {v*=safetyFactor;}
    body.SetLinearVelocity(ecm,{v,0,0});body.SetAngularVelocity(ecm,{0,0,v>.001?w:0.});
    const double yaw=world.Rot().Yaw(),dt=std::chrono::duration<double>(info.dt).count();
    const double yawRate=havePrevious && dt>0 ? std::remainder(yaw-previousYaw,2*M_PI)/dt:0.;
    if(havePrevious)travelled+=std::hypot(current.X()-previous.X(),current.Y()-previous.Y());
    previous=current;previousYaw=yaw;havePrevious=true;
    const double phase=travelled*2*M_PI/1.25;
    for(auto &part:parts) {
      if(part.entity==gz::sim::kNullEntity)part.entity=body.VisualByName(ecm,part.name);
      if(part.entity==gz::sim::kNullEntity)continue;
      double angle=0;
      if(part.kind=="wheel")angle=travelled/std::max(.15,part.radius);
      else if(v>.03) {
        const bool left=part.kind.find("left")!=std::string::npos;
        const bool arm=part.kind.find("arm")!=std::string::npos;
        angle=(left?1:-1)*(arm?-.22:.30)*std::sin(phase);
      }
      const double steer=part.steering && v>.05 ? std::clamp(std::atan(part.wheelbase*yawRate/v),-.45,.45):0.;
      auto pose=gz::math::Pose3d(part.pivot,gz::math::Quaterniond(0,0,steer)*gz::math::Quaterniond(0,angle,0));
      auto component=ecm.Component<gz::sim::components::Pose>(part.entity);
      if(component) {
        component->SetData(pose,[](const auto&a,const auto&b){return a==b;});
        ecm.SetChanged(part.entity,gz::sim::components::Pose::typeId,gz::sim::ComponentState::PeriodicChange);
      }
    }
  }
};
}
GZ_ADD_PLUGIN(fieldlab::CityBody,gz::sim::System,fieldlab::CityBody::ISystemConfigure,fieldlab::CityBody::ISystemPreUpdate)
GZ_ADD_PLUGIN_ALIAS(fieldlab::CityBody,"fieldlab::CityBody")
