# Network patches

Corrections to the OpenStreetMap-based network go **here**, as small
`netconvert` patch files. Never edit `network/deland.net.xml` by hand, and
never fix it in the netedit GUI: the next rebuild would silently undo it.

The build script (`scripts/m1_build_network.py`) applies every patch file in
this folder after the network is built from the OSM snapshot:

| File name ends in | Contains | Example |
|-------------------|----------|---------|
| `.nod.xml` | node (junction) changes | change a junction type |
| `.edg.xml` | edge (road) changes | fix a lane count or speed limit |
| `.con.xml` | connection changes | add or remove a turning movement |
| `.tll.xml` | traffic light changes | add or remove a signal |

Every patch must start with an XML comment saying **what** is wrong, **who
checked it, how, and when** (for example "field visit 2026-11-20, photo"), and
which OSM element it corrects. A patch without evidence is a guess and does
not belong here. If OSM itself is wrong, consider also fixing it on
openstreetmap.org, so everyone benefits.

The SUMO documentation on patch files:
https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html and
https://sumo.dlr.de/docs/Networks/PlainXML.html

No patches exist yet: nothing has been checked in the field so far.
