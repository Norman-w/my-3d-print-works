use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-service-review.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-route-retention.scad>
kind="input-mount-tools";fault=false;
intersection(){crr_all();union(){csr_service_envelope(kind);if(fault)crr_base();}}
