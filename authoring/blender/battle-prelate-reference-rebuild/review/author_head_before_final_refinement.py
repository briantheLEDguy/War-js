"""Serialize the literal, individually authored head control cage.

No coordinates or face connections are inferred.  Each table row is a fixed
modeling decision, including UVs.  The importer may use the listed Blender
Mirror and Subdivision Surface finishing operations.
"""
import json
from pathlib import Path


def part(name, vertex_table, face_table, modifiers, landmarks=None, closed=False):
    vertices = []
    uv_by_id = {}
    for line in vertex_table.strip().splitlines():
        values = line.split()
        vertex_id = values[0]
        vertices.append({"id": vertex_id, "co": [float(v) for v in values[1:4]]})
        uv_by_id[vertex_id] = [float(v) for v in values[4:6]]
    faces = []
    for line in face_table.strip().splitlines():
        values = line.split()
        material = values[-1][1:] if values[-1].startswith("@") else "skin"
        vertex_ids = values[1:-1] if values[-1].startswith("@") else values[1:]
        faces.append({"id": values[0], "vertices": vertex_ids,
                      "uv": [uv_by_id[v] for v in vertex_ids], "material": material})
    return {"id": name, "vertices": vertices, "faces": faces,
            "modifiers": modifiers, "landmarks": landmarks or {}, "seams": [],
            "sharp_edges": [], "creases": [], "closed": closed,
            "transform": {"location": [0, 0, 0], "rotation_degrees": [0, 0, 0],
                          "scale": [1, 1, 1]}}


head = part("head_skin", """
C 0 0.008 1.860 .50 .99
T0 0 -.037 1.847 .50 .96
T1 .031 -.033 1.846 .55 .96
T2 .052 -.012 1.842 .60 .95
T3 .055 .025 1.842 .66 .95
T4 .046 .058 1.840 .73 .95
T5 .026 .077 1.843 .81 .95
T6 0 .081 1.843 .88 .95
F0 0 -.058 1.830 .50 .91
F1 .018 -.056 1.832 .53 .92
F2 .040 -.049 1.830 .58 .91
F3 .059 -.032 1.826 .62 .90
F4 .072 -.010 1.820 .66 .88
F5 .077 .020 1.815 .71 .86
F6 .068 .060 1.815 .77 .86
F7 .043 .089 1.815 .83 .86
F8 0 .097 1.815 .88 .86
W00 0 -.064 1.823 .50 .885
W01 .011 -.066 1.825 .52 .89
W02 .025 -.064 1.824 .55 .885
W03 .045 -.058 1.823 .59 .885
W04 .063 -.040 1.812 .64 .85
W10 0 -.067 1.820 .50 .876
W11 .011 -.070 1.822 .52 .882
W12 .025 -.067 1.821 .55 .88
W13 .045 -.061 1.820 .59 .876
W14 .064 -.042 1.810 .64 .844
W20 0 -.070 1.817 .50 .867
W21 .011 -.075 1.819 .52 .872
W22 .025 -.070 1.818 .55 .87
W23 .045 -.064 1.817 .59 .867
W24 .065 -.046 1.808 .64 .84
D0 0 -.084 1.805 .50 .83
D1 .012 -.089 1.810 .52 .85
D2 .025 -.084 1.807 .55 .84
D3 .048 -.074 1.808 .60 .845
D4 .067 -.050 1.796 .65 .81
D5 .077 -.016 1.790 .69 .79
D6 .073 .055 1.785 .77 .77
D7 .044 .088 1.786 .83 .78
D8 0 .095 1.790 .88 .79
BR0 0 -.098 1.779 .50 .795
BR1 .009 -.114 1.780 .515 .798
BR2 .020 -.119 1.778 .537 .792
BR3 .037 -.115 1.783 .57 .810
BR4 .053 -.100 1.783 .61 .810
BR5 .067 -.073 1.768 .65 .765
B0 0 -.107 1.763 .50 .78
B1 .009 -.113 1.765 .515 .785
B2 .019 -.125 1.758 .537 .77
B3 .034 -.123 1.765 .57 .79
B4 .052 -.109 1.771 .61 .79
B5 .067 -.079 1.757 .65 .745
B6 .078 -.028 1.768 .70 .72
B7 .073 .052 1.762 .77 .70
B8 .043 .083 1.761 .83 .70
B9 0 .090 1.770 .88 .73
N0 0 -.118 1.750 .50 .72
N1 .011 -.111 1.750 .52 .715
U0 .016 -.101 1.750 .535 .715
U1 .025 -.106 1.751 .55 .732
U2 .039 -.104 1.755 .58 .738
U3 .050 -.097 1.756 .605 .728
U4 .058 -.084 1.751 .625 .71
S0 .066 -.070 1.741 .65 .67
S1 .076 -.026 1.732 .70 .645
S2 .067 .057 1.738 .77 .63
S3 .040 .083 1.735 .83 .62
S4 0 .087 1.743 .88 .645
N2 0 -.132 1.731 .50 .66
N3 .014 -.123 1.733 .529 .658
L0 .017 -.100 1.747 .537 .70
L1 .026 -.102 1.744 .553 .689
L2 .040 -.099 1.744 .584 .689
L3 .050 -.091 1.745 .606 .689
L4 .059 -.081 1.749 .627 .70
E0 .018 -.103 1.7495 .539 .712
E1 .027 -.108 1.7500 .555 .726
E2 .039 -.106 1.7525 .58 .728
E3 .050 -.099 1.7530 .605 .722
E4 .057 -.087 1.7510 .623 .71
E5 .0575 -.086 1.7490 .624 .704
E6 .049 -.093 1.7470 .604 .695
E7 .039 -.101 1.7460 .582 .695
E8 .027 -.104 1.7460 .555 .695
E9 .019 -.103 1.7475 .541 .704
K0 .024 -.107 1.737 .55 .668
K1 .039 -.105 1.733 .58 .654
K2 .053 -.106 1.736 .611 .666
K3 .063 -.098 1.728 .64 .64
NTOP0 0 -.141 1.721 .50 .63
NTOP1 .008 -.139 1.723 .517 .633
NTOP2 .016 -.133 1.722 .535 .63
NTOP3 .023 -.122 1.722 .55 .63
TN0 0 -.147 1.711 .50 .615
TN1 .009 -.143 1.715 .516 .618
TN2 .021 -.132 1.713 .54 .603
TN3 .027 -.122 1.712 .553 .60
TN4 .032 -.107 1.709 .57 .60
TN5 .054 -.110 1.713 .616 .60
TN6 .068 -.055 1.699 .66 .543
TN7 .062 .015 1.704 .72 .522
TN8 .040 .068 1.718 .80 .565
TN9 0 .076 1.729 .88 .60
A0 0 -.138 1.707 .50 .59
A1 .007 -.127 1.705 .514 .58
A2 .014 -.133 1.709 .53 .586
A3 .023 -.122 1.707 .544 .58
A4 .027 -.120 1.706 .551 .592
A5 .034 -.109 1.696 .565 .565
A6 .050 -.058 1.697 .608 .54
A7 .064 -.035 1.689 .65 .50
A8 .057 .020 1.689 .72 .48
A9 .038 .066 1.700 .80 .51
A10 0 .071 1.707 .88 .532
P0 0 -.111 1.694 .50 .54
P1 .008 -.113 1.695 .517 .543
P2 .018 -.115 1.691 .539 .531
P3 .026 -.108 1.684 .557 .507
P4 .038 -.106 1.681 .574 .489
P5 .050 -.056 1.681 .61 .48
P6 .068 -.035 1.681 .655 .442
P7 .055 .019 1.675 .72 .43
P8 .030 .055 1.683 .80 .46
P9 0 .059 1.688 .88 .475
NT0 .010 -.130 1.7060 .52 .585
NT1 .016 -.130 1.7065 .532 .587
NT2 .020 -.124 1.7060 .54 .585
NT3 .016 -.122 1.7030 .532 .576
NT4 .010 -.124 1.7030 .52 .576
NC0 .014 -.116 1.7050 .529 .581
MU0 0 -.118 1.686 .50 .507
MU1 .008 -.120 1.687 .517 .514
MU2 .020 -.117 1.684 .543 .504
MU3 .030 -.109 1.680 .565 .492
MU4 .035 -.098 1.679 .582 .483
ML0 0 -.123 1.681 .50 .495
ML1 .009 -.123 1.682 .52 .498
ML2 .020 -.120 1.680 .543 .495
ML3 .029 -.110 1.6785 .564 .486
MD0 0 -.121 1.6804 .50 .493
MD1 .009 -.121 1.6814 .52 .496
MD2 .020 -.118 1.6794 .543 .493
MD3 .029 -.109 1.6779 .564 .484
LL0 0 -.122 1.676 .50 .483
LL1 .010 -.122 1.677 .521 .486
LL2 .020 -.117 1.676 .543 .483
LL3 .029 -.108 1.675 .564 .48
CC0 0 -.107 1.668 .50 .447
CC1 .013 -.108 1.668 .528 .447
CC2 .030 -.095 1.668 .563 .441
CC3 .050 -.073 1.672 .594 .438
CC4 .065 -.045 1.673 .65 .42
CC5 .052 .002 1.675 .72 .381
CC6 .030 .035 1.665 .80 .40
CC7 0 .041 1.670 .88 .42
CH0 0 -.098 1.664 .50 .403
CH1 .015 -.097 1.665 .532 .406
CH2 .034 -.086 1.662 .567 .403
CH3 .048 -.063 1.661 .60 .387
CH4 .050 -.018 1.663 .70 .363
CH5 .026 .021 1.650 .80 .36
CH6 0 .032 1.660 .88 .39
Z0 0 -.082 1.650 .50 .36
Z1 .021 -.078 1.651 .545 .363
Z2 .035 -.057 1.650 .60 .36
Z3 .037 -.019 1.637 .70 .321
Z4 .027 .019 1.635 .80 .315
Z5 0 .033 1.638 .88 .324
Q0 0 -.050 1.590 .50 .18
Q1 .024 -.044 1.590 .555 .18
Q2 .041 -.024 1.590 .63 .18
Q3 .043 .003 1.590 .71 .18
Q4 .032 .033 1.590 .80 .18
Q5 0 .046 1.590 .88 .18
""", """
cap01 C T0 T1
cap02 C T1 T2
cap03 C T2 T3
cap04 C T3 T4
cap05 C T4 T5
cap06 C T5 T6
scalp01 T0 F0 F1 T1
scalp02 T1 F1 F2 T2
scalp03 T2 F2 F3
scalp04 T2 F3 F4 T3
scalp05 T3 F4 F5 T4
scalp06 T4 F5 F6 T5
scalp07 T5 F6 F7 T6
scalp08 T6 F7 F8
forehead01 F0 W00 W01 F1
forehead02 F1 W01 W02 F2
forehead03 F2 W02 W03 F3
forehead04 F3 W03 W04 F4
furrow01 W00 W10 W11 W01
furrow02 W01 W11 W12 W02
furrow03 W02 W12 W13 W03
furrow04 W03 W13 W14 W04
furrow05 W10 W20 W21 W11
furrow06 W11 W21 W22 W12
furrow07 W12 W22 W23 W13
furrow08 W13 W23 W24 W14
forehead05 W20 D0 D1 W21
forehead06 W21 D1 D2 W22
forehead07 W22 D2 D3 W23
forehead08 W23 D3 D4 W24
temple01 F4 W04 D5 F5
temple02 W04 W14 D5
temple03 W14 W24 D5
temple04 W24 D4 D5
temple05 F5 D5 D6 F6
temple06 F6 D6 D7 F7
temple07 F7 D7 D8 F8
supraorbital01 D0 BR0 BR1 D1
supraorbital02 D1 BR1 BR2 D2
supraorbital03 D2 BR2 BR3 D3
supraorbital04 D3 BR3 BR4 D4
supraorbital05 D4 BR4 BR5
supraorbital06 D4 BR5 B6 D5
frontalridge01 BR0 B0 B1 BR1
frontalridge02 BR1 B1 B2 BR2
frontalridge03 BR2 B2 B3 BR3
frontalridge04 BR3 B3 B4 BR4
frontalridge05 BR4 B4 B5 BR5
frontalridge06 BR5 B5 B6
supraorbital07 D5 B6 B7 D6
supraorbital08 D6 B7 B8 D7
supraorbital09 D7 B8 B9 D8
glabella01 B0 N0 N1 B1
glabella02 B1 N1 U0 B2
upperorbit01 B2 U0 U1 B3
upperorbit02 B3 U1 U2 B4
upperorbit03 B4 U2 U3 B5
upperorbit04 B5 U3 U4
lateralorbit01 B5 U4 S0
lateralorbit02 B5 S0 S1 B6
lateralorbit03 B6 S1 S2 B7
lateralorbit04 B7 S2 S3 B8
lateralorbit05 B8 S3 S4 B9
nasalbridge01 N0 N2 N3 N1
nasalbridge02 N1 N3 L0 U0
eyelid01 U0 E0 E1 U1
eyelid02 U1 E1 E2 U2
eyelid03 U2 E2 E3 U3
eyelid04 U3 E3 E4 U4
eyelid05 U4 E4 E5 L4
eyelid06 L4 E5 E6 L3
eyelid07 L3 E6 E7 L2
eyelid08 L2 E7 E8 L1
eyelid09 L1 E8 E9 L0
eyelid10 L0 E9 E0 U0
infraorbital01 L0 N3 K0 L1
infraorbital02 L1 K0 K1 L2
infraorbital03 L2 K1 K2 L3
infraorbital04 L3 K2 K3 L4
infraorbital05 L4 K3 S0
outercanthus01 U4 L4 S0
nasaldorsum01 N2 NTOP0 NTOP1 N3
nasaldorsum02 N3 NTOP1 NTOP2
nasalwing01 N3 NTOP2 NTOP3 K0
nasaltip_support01 NTOP0 TN0 TN1 NTOP1
nasaltip_support02 NTOP1 TN1 TN2 NTOP2
nasaltip_support03 NTOP2 TN2 TN3 NTOP3
nasaltip_support04 NTOP3 TN3 K0
malar01 K0 TN3 TN4 K1
malar02 K1 TN4 TN5 K2
malar03 K2 TN5 TN6 K3
malar04 K3 TN6 S1 S0
malar05 S1 TN6 TN7 S2
occiput01 S2 TN7 TN8 S3
occiput02 S3 TN8 TN9 S4
nosetip01 TN0 A0 A1 TN1
nosetip02 TN1 A1 A2 TN2
nosetip03 TN2 A2 A3 TN3
ala01 TN3 A3 A4
nasolabial01 TN3 A4 A5 TN4
nasolabial02 TN4 A5 A6 TN5
nasolabial03 TN5 A6 A7 TN6
masseter01 TN6 A7 A8 TN7
masseter02 TN7 A8 A9 TN8
nape01 TN8 A9 A10 TN9
philtrum01 A0 P0 P1 A1
alarbase01 A1 NT0 NT1 A2
alarbase02 A2 NT1 NT2 A3
alarbase03 A3 NT2 NT3 P2
alarbase04 P2 NT3 NT4 P1
alarbase05 P1 NT4 NT0 A1
nostril01 NT0 NC0 NT1 @brow
nostril02 NT1 NC0 NT2 @brow
nostril03 NT2 NC0 NT3 @brow
nostril04 NT3 NC0 NT4 @brow
nostril05 NT4 NC0 NT0 @brow
nasolabial04 A3 P2 P3 A4
nasolabial05 A4 P3 P4 A5
nasolabial06 A5 P4 P5 A6
buccal01 A6 P5 P6 A7
buccal02 A7 P6 P7 A8
nape02 A8 P7 P8 A9
nape03 A9 P8 P9 A10
upperlipbase01 P0 MU0 MU1 P1
upperlipbase02 P1 MU1 MU2 P2
upperlipbase03 P2 MU2 MU3 P3
upperlipbase04 P3 MU3 MU4 P4
upperlip01 MU0 ML0 ML1 MU1
upperlip02 MU1 ML1 ML2 MU2
upperlip03 MU2 ML2 ML3 MU3
upperlip04 MU3 ML3 MU4
mouthcrease01 ML0 MD0 MD1 ML1 @brow
mouthcrease02 ML1 MD1 MD2 ML2 @brow
mouthcrease03 ML2 MD2 MD3 ML3 @brow
mouthcrease04 ML3 MD3 MU4 @brow
lowerlip01 MD0 LL0 LL1 MD1
lowerlip02 MD1 LL1 LL2 MD2
lowerlip03 MD2 LL2 LL3 MD3
lowerlip04 MD3 LL3 MU4
labiomental01 LL0 CC0 CC1 LL1
labiomental02 LL1 CC1 CC2 LL2
labiomental03 LL2 CC2 CC3 LL3
labiomental04 LL3 CC3 MU4
marionette01 MU4 CC3 P5 P4
mandible01 P5 CC3 CC4 P6
mandible02 P6 CC4 CC5 P7
mandible03 P7 CC5 CC6 P8
nape04 P8 CC6 CC7 P9
chin01 CC0 CH0 CH1 CC1
chin02 CC1 CH1 CH2 CC2
chin03 CC2 CH2 CH3 CC3
chin04 CC3 CH3 CH4 CC4
chin05 CC4 CH4 CC5
jaw01 CC5 CH4 CH5 CC6
nape05 CC6 CH5 CH6 CC7
chin06 CH0 Z0 Z1 CH1
chin07 CH1 Z1 Z2 CH2
chin08 CH2 Z2 CH3
jaw02 CH3 Z2 Z3 CH4
jaw03 CH4 Z3 Z4 CH5
nape06 CH5 Z4 Z5 CH6
neck01 Z0 Q0 Q1 Z1
neck02 Z1 Q1 Q2 Z2
neck03 Z2 Q2 Q3 Z3
neck04 Z3 Q3 Q4 Z4
neck05 Z4 Q4 Q5 Z5
""", [{"type": "MIRROR", "axis": "X"}, {"type": "SUBSURF", "levels": 2}],
    {"crown": "C", "chin": "Z0", "nose_tip": "TN0", "eye_inner_left": "E0",
     "eye_outer_left": "E4", "stern_mouth_center": "ML0", "jaw_corner_left": "CH3"})

head["creases"] = [
    {"edge": ["D1", "BR1"], "value": .55},
    {"edge": ["BR1", "B1"], "value": .55},
    {"edge": ["B1", "B2"], "value": .30},
    {"edge": ["B2", "B3"], "value": .50},
    {"edge": ["B3", "B4"], "value": .40},
    {"edge": ["B4", "B5"], "value": .20},
    {"edge": ["E0", "E1"], "value": .40},
    {"edge": ["E1", "E2"], "value": .40},
    {"edge": ["E2", "E3"], "value": .40},
    {"edge": ["E3", "E4"], "value": .40},
    {"edge": ["E4", "E5"], "value": .40},
    {"edge": ["E5", "E6"], "value": .40},
    {"edge": ["E6", "E7"], "value": .40},
    {"edge": ["E7", "E8"], "value": .40},
    {"edge": ["E8", "E9"], "value": .40},
    {"edge": ["E9", "E0"], "value": .40},
    {"edge": ["TN1", "TN2"], "value": .25},
    {"edge": ["TN2", "TN3"], "value": .25},
    {"edge": ["A4", "P3"], "value": .40},
    {"edge": ["A4", "A5"], "value": .55},
    {"edge": ["A5", "P4"], "value": .55},
    {"edge": ["P4", "MU4"], "value": .35},
    {"edge": ["P3", "MU3"], "value": .25},
    {"edge": ["K1", "K2"], "value": .35},
    {"edge": ["K2", "K3"], "value": .45},
    {"edge": ["K3", "TN6"], "value": .30},
    {"edge": ["CC3", "CC4"], "value": .30},
    {"edge": ["CC4", "CC5"], "value": .35},
    {"edge": ["CH2", "CH3"], "value": .25},
    {"edge": ["CH3", "CH4"], "value": .25},
    {"edge": ["ML0", "ML1"], "value": .25},
    {"edge": ["ML1", "ML2"], "value": .25},
    {"edge": ["ML2", "ML3"], "value": .25},
]

eye = part("eyes", """
O0 .012 -.0850 1.7520 .05 .55
O1 .023 -.0880 1.7620 .20 .82
O2 .039 -.0860 1.7650 .55 .92
O3 .052 -.0770 1.7610 .85 .78
O4 .062 -.0640 1.7530 .98 .51
O5 .062 -.0630 1.7460 .98 .40
O6 .051 -.0740 1.7360 .85 .22
O7 .039 -.0830 1.7330 .55 .14
O8 .024 -.0860 1.7360 .20 .22
O9 .013 -.0840 1.7450 .06 .40
I0 .0285 -.0978 1.7495 .32 .50
I1 .0310 -.0983 1.7555 .36 .70
I2 .0370 -.0988 1.7580 .48 .80
I3 .0430 -.0983 1.7555 .60 .70
I4 .0455 -.0978 1.7495 .64 .50
I5 .0430 -.0983 1.7435 .60 .30
I6 .0370 -.0988 1.7410 .48 .20
I7 .0310 -.0983 1.7435 .36 .30
P0 .0334 -.0994 1.7495 .42 .50
P1 .0345 -.0995 1.7520 .44 .60
P2 .0370 -.0996 1.7531 .48 .64
P3 .0395 -.0995 1.7520 .53 .60
P4 .0406 -.0994 1.7495 .55 .50
P5 .0395 -.0995 1.7470 .53 .40
P6 .0370 -.0996 1.7459 .48 .36
P7 .0345 -.0995 1.7470 .44 .40
PC .0370 -.0998 1.7495 .48 .50
""", """
sclera01 O0 O1 I1 I0 @eye_white
sclera02 O1 O2 I2 I1 @eye_white
sclera03 O2 O3 I3 I2 @eye_white
sclera04 O3 O4 I4 I3 @eye_white
sclera05 O4 O5 I4 @eye_white
sclera06 O5 O6 I5 I4 @eye_white
sclera07 O6 O7 I6 I5 @eye_white
sclera08 O7 O8 I7 I6 @eye_white
sclera09 O8 O9 I0 I7 @eye_white
sclera10 O9 O0 I0 @eye_white
iris01 I0 I1 P1 P0 @iris
iris02 I1 I2 P2 P1 @iris
iris03 I2 I3 P3 P2 @iris
iris04 I3 I4 P4 P3 @iris
iris05 I4 I5 P5 P4 @iris
iris06 I5 I6 P6 P5 @iris
iris07 I6 I7 P7 P6 @iris
iris08 I7 I0 P0 P7 @iris
pupil01 P0 P1 PC @pupil
pupil02 P1 P2 PC @pupil
pupil03 P2 P3 PC @pupil
pupil04 P3 P4 PC @pupil
pupil05 P4 P5 PC @pupil
pupil06 P5 P6 PC @pupil
pupil07 P6 P7 PC @pupil
pupil08 P7 P0 PC @pupil
""", [{"type": "MIRROR", "axis": "X"}, {"type": "SUBSURF", "levels": 2}])

ear = part("ears", """
O0 .069 -.022 1.782 .08 .83
O1 .078 -.019 1.790 .24 .98
O2 .085 -.006 1.787 .60 .94
O3 .090 .006 1.777 .87 .76
O4 .091 .010 1.759 .98 .49
O5 .085 .001 1.740 .76 .19
O6 .079 -.006 1.731 .47 .04
O7 .073 -.014 1.733 .22 .08
O8 .068 -.022 1.746 .06 .28
O9 .069 -.024 1.761 .04 .53
H0 .073 -.025 1.780 .15 .80
H1 .079 -.022 1.785 .30 .89
H2 .084 -.010 1.782 .58 .84
H3 .087 -.001 1.772 .77 .70
H4 .087 .002 1.757 .81 .47
H5 .082 -.006 1.742 .62 .23
H6 .078 -.011 1.737 .43 .15
H7 .074 -.016 1.739 .27 .19
H8 .072 -.023 1.749 .15 .34
H9 .072 -.025 1.763 .13 .55
C0 .074 -.017 1.776 .23 .73
C1 .079 -.015 1.778 .36 .77
C2 .082 -.005 1.773 .54 .69
C3 .083 -.002 1.761 .58 .52
C4 .079 -.007 1.750 .46 .35
C5 .076 -.013 1.745 .31 .27
C6 .073 -.015 1.750 .22 .35
T0 .070 -.026 1.765 .07 .58
T1 .075 -.028 1.760 .21 .50
T2 .074 -.027 1.752 .18 .38
T3 .070 -.022 1.752 .08 .38
F0 .074 -.007 1.767 .31 .61
F1 .077 -.005 1.762 .39 .53
F2 .075 -.006 1.756 .34 .44
R0 .068 -.015 1.782 .08 .83
R1 .077 -.012 1.790 .24 .98
R2 .084 .001 1.787 .60 .94
R3 .089 .013 1.777 .87 .76
R4 .090 .017 1.759 .98 .49
R5 .084 .008 1.740 .76 .19
R6 .078 .001 1.731 .47 .04
R7 .072 -.007 1.733 .22 .08
R8 .067 -.015 1.746 .06 .28
R9 .068 -.017 1.761 .04 .53
BC .077 .018 1.760 .50 .50
""", """
helix01 O0 O1 H1 H0
helix02 O1 O2 H2 H1
helix03 O2 O3 H3 H2
helix04 O3 O4 H4 H3
helix05 O4 O5 H5 H4
helix06 O5 O6 H6 H5
lobule01 O6 O7 H7 H6
lobule02 O7 O8 H8 H7
helix07 O8 O9 H9 H8
helix08 O9 O0 H0 H9
antihelix01 H0 H1 C1 C0
antihelix02 H1 H2 C2 C1
antihelix03 H2 H3 C3 C2
antihelix04 H3 H4 C4 C3
antihelix05 H4 H5 C5 C4
antihelix06 H5 H6 C6 C5
antihelix07 H6 H7 C6
antihelix08 H7 H8 T3 C6
tragus01 H8 H9 T0 T3
tragus02 H9 H0 C0 T0
tragus03 T0 C0 F0 T1
tragus04 T1 F0 F1 T2
tragus05 T2 F1 F2 T3
tragus06 T0 T1 T2 T3
concha01 C0 C1 C2 F0
concha02 C2 C3 F1 F0
concha03 C3 C4 F2 F1
concha04 C4 C5 C6 F2
concha05 C6 T3 F2
rim01 O1 O0 R0 R1
rim02 O2 O1 R1 R2
rim03 O3 O2 R2 R3
rim04 O4 O3 R3 R4
rim05 O5 O4 R4 R5
rim06 O6 O5 R5 R6
rim07 O7 O6 R6 R7
rim08 O8 O7 R7 R8
rim09 O9 O8 R8 R9
rim10 O0 O9 R9 R0
back01 R1 R0 BC
back02 R2 R1 BC
back03 R3 R2 BC
back04 R4 R3 BC
back05 R5 R4 BC
back06 R6 R5 BC
back07 R7 R6 BC
back08 R8 R7 BC
back09 R9 R8 BC
back10 R0 R9 BC
""", [{"type": "MIRROR", "axis": "X"}, {"type": "SUBSURF", "levels": 2}],
    {"helix_peak_left": "O1", "ear_lobe_left": "O6"}, closed=True)

brow = part("eyebrows", """
I0 .012 -.120 1.762 .02 .45
I1 .023 -.124 1.765 .20 .55
I2 .037 -.119 1.771 .45 .65
I3 .050 -.110 1.774 .70 .60
I4 .061 -.091 1.760 .96 .34
O0 .012 -.1205 1.765 .03 .62
O1 .023 -.1245 1.769 .22 .78
O2 .037 -.1195 1.774 .47 .89
O3 .050 -.1105 1.777 .72 .77
O4 .061 -.0915 1.762 .98 .40
""", """
brow01 I0 I1 O1 O0 @brow
brow02 I1 I2 O2 O1 @brow
brow03 I2 I3 O3 O2 @brow
brow04 I3 I4 O4 O3 @brow
""", [{"type": "MIRROR", "axis": "X"}, {"type": "SUBSURF", "levels": 2},
         {"type": "SOLIDIFY", "thickness": .0007, "offset": 0}])

for face in ear["faces"]:
    face["material"]="skin_ear"

document = {
    "schema_version": 1,
    "component": "head",
    "reference_notes": [
        "Fresh literal control cage; no source geometry from prior attempts.",
        "The main front view governs the lowered heavy inner brow, bald cranium, broad nose, cheek hollows, compressed mouth and squared chin.",
        "The side view governs projected nasal dorsum, forehead slope, jaw depth and pinna silhouette. Hidden scalp and neck are conservative interpretations.",
        "Mirror is an authorized finishing modifier; the explicit left-half cage, ear, eye surfaces and brow are individually inspectable.",
        "The head cage deliberately has eye apertures and an open neck end concealed by the gorget. Eye surfaces overlap beneath the eyelid rims.",
        "The user accepted this modeling direction for full-character continuation. Dedicated UV-matched skin maps and later runtime review are recorded separately."
    ],
    "parts": [head, eye, ear, brow]
}

if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[1] / "source" / "head.json"
    destination.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(destination)
    print({"parts": len(document["parts"]),
           "control_vertices": sum(len(p["vertices"]) for p in document["parts"]),
           "control_faces": sum(len(p["faces"]) for p in document["parts"])})
