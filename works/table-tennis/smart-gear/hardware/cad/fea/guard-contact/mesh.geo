// mm. Actual validated v1.16 body, excluding decorative lettering only.
Merge "../../exports/perpendicular-u-joint-v1.16-root-radius/guard-v1.16-body.stl";
ClassifySurfaces{40*Pi/180,1,0,Pi};
CreateGeometry;
Surface Loop(1) = Surface{:};
Volume(1) = {1};
Physical Volume("CLIP") = {1};
Mesh.MeshSizeMin = 1.2;
Mesh.MeshSizeMax = 3;
Mesh.Algorithm3D = 1;
Mesh.ElementOrder = 1;
Mesh.Optimize = 1;
