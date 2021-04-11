//Maya ASCII 2019 scene
//Name: surface.ma
//Last modified: Thu, Mar 25, 2021 06:43:48 PM
//Codeset: 932
requires maya "2019";
requires "mtoa" "4.0.2.1";
requires "stereoCamera" "10.0";
currentUnit -l centimeter -a degree -t film;
fileInfo "application" "maya";
fileInfo "product" "Maya 2019";
fileInfo "version" "2019";
fileInfo "cutIdentifier" "202004141915-92acaa8c08";
fileInfo "osv" "Microsoft Windows 10 Technical Preview  (Build 18363)\n";
createNode transform -n "sliding_surface";
	rename -uid "7AD18585-4AAE-47A9-57F6-2DAECD889EC6";
	setAttr ".t" -type "double3" 0.068651186765702477 28.962347498161602 2.6494267605940083 ;
	setAttr ".r" -type "double3" 92.794051217800103 0 0 ;
	setAttr ".s" -type "double3" 5.0471796954997385 3.8580733098249835 4.1560980029309285 ;
createNode nurbsSurface -n "sliding_surfaceShape" -p "sliding_surface";
	rename -uid "4B8D57F6-437A-689D-58FA-A9A3F15A026C";
	setAttr -k off ".v";
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
	setAttr ".dvu" 0;
	setAttr ".dvv" 0;
	setAttr ".cpr" 4;
	setAttr ".cps" 4;
	setAttr ".cc" -type "nurbsSurface" 
		3 3 0 0 no 
		11 0 0 0 0.16666666666666666 0.33333333333333331 0.5 0.66666666666666663 0.83333333333333326
		 1 1 1
		11 0 0 0 0.16666666666666666 0.33333333333333331 0.5 0.66666666666666663 0.83333333333333326
		 1 1 1
		
		81
		-0.20860575635753736 -0.47886715952800385 0.50828289757255174
		-0.21411531104601539 -0.47856232274384924 0.45410032431572223
		-0.22319662396198453 -0.47618177645092508 0.34882945492883
		-0.24924343417367822 -0.43368702804761017 0.18008626169826325
		-0.26144769725863731 -0.44079203933950784 0.013047060165605195
		-0.26539414715227216 -0.45864607899223075 -0.1455989942153515
		-0.26465029066377427 -0.47069950566616348 -0.30552098225341418
		-0.24805820960870353 -0.48162804866368503 -0.38710721659782177
		-0.23516578361497217 -0.47753585067043514 -0.41850605546299935
		-0.18867333594442059 -0.44532391769170665 0.50297120085957392
		-0.19218989659098773 -0.44188365372867111 0.44584149030819109
		-0.20736174412507455 -0.37593124892892321 0.28734551218357396
		-0.24310807071148965 -0.37261278478380172 0.17726143288415042
		-0.25712768941040531 -0.37470095859323005 0.011193254351329784
		-0.2516530435899656 -0.39135566492715446 -0.14628631287357763
		-0.25019005969607955 -0.40668403667289343 -0.31028065905759394
		-0.23711109091495514 -0.41096407852375255 -0.38366737248751015
		-0.22109179399980194 -0.42111403100944617 -0.42150147215868472
		-0.13004922996587198 -0.24101687252185927 0.36814738338553532
		-0.14019394069353988 -0.25785798142323557 0.35844767919420484
		-0.16688597448917925 -0.27697854699725755 0.3073244480988846
		-0.20606094002982539 -0.28476193902884389 0.15028013238800231
		-0.2264132470475104 -0.25739615198116811 0.005349510427148374
		-0.22416514428862913 -0.24742110584300087 -0.151182029761185
		-0.20816023133872313 -0.28686538286505031 -0.31088450094476183
		-0.19757432967700758 -0.30473725331714591 -0.38667970159567311
		-0.19251698418167051 -0.32365065018562439 -0.41818818580393913
		-0.079828778540568995 -0.15517101814906409 0.38288296073671546
		-0.080196638413695065 -0.15288316626032272 0.38097219980272889
		-0.093399943465841712 -0.14849954055182807 0.32871106785321391
		-0.10227780830192901 -0.1388776042347189 0.17526435164672538
		-0.12531466159544163 -0.17418274871012146 0.016066786580998915
		-0.13657272429982933 -0.13891335448736714 -0.15609975182300762
		-0.12341663951454715 -0.17002641253179812 -0.29716065895830202
		-0.11504738011629537 -0.20161231586501099 -0.38025955961977509
		-0.10996499849097136 -0.21035644640280654 -0.39935981037390711
		0.0028979360136856258 -0.13672795053971321 0.3844830791006606
		-0.0025520737234196317 -0.11758890825700091 0.36120239636350604
		-0.0046653659270615312 -0.11161868773881084 0.32628206901998702
		-0.0085093009136186417 -0.051303342604145485 0.11064812379316624
		-0.0050659270307026414 -0.038930733731753486 0.026244160930933624
		0.00057425691359328304 -0.11253927183756846 -0.17813681317528207
		-0.0035222060461695091 -0.13315020058349719 -0.29298175261520321
		-0.0063659015089086108 -0.16768812436352765 -0.37893165641089599
		-0.0057470795278412191 -0.17477755043210896 -0.39448024472897014
		0.060363641219593984 -0.15972970852300339 0.37831187953605205
		0.069833870338767812 -0.16852624842317776 0.37489401129460731
		0.078936003394910026 -0.16334993876743592 0.3291224163204225
		0.10198008409953208 -0.16439666125442043 0.17386304650465245
		0.1224906974014032 -0.18585926357621096 0.017400783049665414
		0.12807467552911589 -0.15004119995461423 -0.15748956252308499
		0.10214992826060365 -0.17463119113375647 -0.29736970381283179
		0.09819514086330336 -0.2076716694986413 -0.3775139930049205
		0.094640506403963653 -0.21495022899959343 -0.39454822203317175
		0.10911110610851144 -0.25141839377375708 0.36215657692007053
		0.12181521789055821 -0.27244170928781242 0.35003056008870725
		0.1474342881833246 -0.29138576394949411 0.30169982600955425
		0.18776639530917708 -0.29529034438946899 0.14713692073955453
		0.20386984668767305 -0.26768854061000447 0.0065201750199310737
		0.19979153196977695 -0.2593607089423306 -0.14897919530122294
		0.18791358885830767 -0.30191411309799815 -0.30733698742713145
		0.18017444869954249 -0.31802034920968852 -0.37703041660385228
		0.17351318479368547 -0.33521587675768194 -0.41447731821574063
		0.16662971342469934 -0.45253369989823755 0.50121917592297738
		0.17538428122534874 -0.45625792351292438 0.44461529814367662
		0.18590276247852877 -0.38022961819507617 0.27911211671776748
		0.21800878852686592 -0.38139484216998221 0.17363476681944245
		0.23133592204173795 -0.38081368517722808 0.006555195196797925
		0.22705937313612473 -0.40224827151936804 -0.14726176753493814
		0.22592022922172028 -0.41560047926854182 -0.3042384996331382
		0.21228432464333988 -0.4140943709238859 -0.3785228039019648
		0.20345070408130728 -0.43252624865856942 -0.40731969252146172
		0.18682335987333992 -0.48989750668389559 0.5076095843979056
		0.19072465025703611 -0.48549290919212951 0.45123566992387065
		0.19816652180069258 -0.48068878702167772 0.34404835017606761
		0.22243909706098366 -0.43350237077121762 0.17631664211872522
		0.2350302628302027 -0.4418328440437897 0.0075966073989501837
		0.27947820344044583 -0.52164244369919011 -0.13547564104408938
		0.23988812233132331 -0.47985123021468173 -0.30139887306149582
		0.22241635197308046 -0.48276171686703356 -0.38363277542844276
		0.21308524461301551 -0.48890485548632356 -0.41105936487327277
		
		;
	setAttr ".nufa" 4.5;
	setAttr ".nvfa" 4.5;
createNode transform -s -n "persp";
	rename -uid "53CE9867-43AD-C0A5-43CE-64B572256570";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 6.5761389801573387 33.68889723577422 8.0325008159970821 ;
	setAttr ".r" -type "double3" -27.938352729602325 45.000000000000007 2.9236893181567143e-14 ;
createNode camera -s -n "perspShape" -p "persp";
	rename -uid "AACF5499-4A08-05F3-5E99-B4BF11373757";
	setAttr -k off ".v" no;
	setAttr ".fl" 34.999999999999993;
	setAttr ".coi" 10.360167632613791;
	setAttr ".imn" -type "string" "persp";
	setAttr ".den" -type "string" "persp_depth";
	setAttr ".man" -type "string" "persp_mask";
	setAttr ".tp" -type "double3" 0.10419356822967529 28.834938176828601 1.5605554040694978 ;
	setAttr ".hc" -type "string" "viewSet -p %camera";
	setAttr ".ai_translator" -type "string" "perspective";
createNode transform -s -n "top";
	rename -uid "8953A5DE-4E48-8EBA-CE3C-8895661B1CC1";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 0 1000.1 0 ;
	setAttr ".r" -type "double3" -90 0 0 ;
createNode camera -s -n "topShape" -p "top";
	rename -uid "407839C4-4458-5F36-B68A-2481085A40EE";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "top";
	setAttr ".den" -type "string" "top_depth";
	setAttr ".man" -type "string" "top_mask";
	setAttr ".hc" -type "string" "viewSet -t %camera";
	setAttr ".o" yes;
	setAttr ".ai_translator" -type "string" "orthographic";
createNode transform -s -n "front";
	rename -uid "BDBD32AD-4CE0-BE52-8C84-39A601879619";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 0 0 1000.1 ;
createNode camera -s -n "frontShape" -p "front";
	rename -uid "2030322C-45B4-1C2D-EFDE-ED83D0A5E709";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "front";
	setAttr ".den" -type "string" "front_depth";
	setAttr ".man" -type "string" "front_mask";
	setAttr ".hc" -type "string" "viewSet -f %camera";
	setAttr ".o" yes;
	setAttr ".ai_translator" -type "string" "orthographic";
createNode transform -s -n "side";
	rename -uid "716937FE-4E8C-729E-F437-21B8415CB949";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 1000.1 0 0 ;
	setAttr ".r" -type "double3" 0 90 0 ;
createNode camera -s -n "sideShape" -p "side";
	rename -uid "73CADFEF-4389-029F-E321-43ACAC179361";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 1000.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "side";
	setAttr ".den" -type "string" "side_depth";
	setAttr ".man" -type "string" "side_mask";
	setAttr ".hc" -type "string" "viewSet -s %camera";
	setAttr ".o" yes;
	setAttr ".ai_translator" -type "string" "orthographic";
createNode lightLinker -s -n "lightLinker1";
	rename -uid "5FA0ABCD-4BEA-2028-B6B6-C7BE6AEBD913";
	setAttr -s 2 ".lnk";
	setAttr -s 2 ".slnk";
createNode shapeEditorManager -n "shapeEditorManager";
	rename -uid "51EF62A2-440B-C55B-61C6-6F84E201181D";
createNode poseInterpolatorManager -n "poseInterpolatorManager";
	rename -uid "9882C7FB-46FF-6807-1D0C-DDBFD550CFF6";
createNode displayLayerManager -n "layerManager";
	rename -uid "29500969-426F-3D1C-20BE-69B6E438E268";
createNode displayLayer -n "defaultLayer";
	rename -uid "02449A86-496F-3E28-4282-E2AD1931F393";
createNode renderLayerManager -n "renderLayerManager";
	rename -uid "9F42C1D8-4FD6-E2B0-DDAA-96B2D81E526D";
createNode renderLayer -n "defaultRenderLayer";
	rename -uid "013C5EA7-4EC6-2189-1ED9-57BA51AD01D9";
	setAttr ".g" yes;
createNode script -n "sceneConfigurationScriptNode";
	rename -uid "2E931827-438D-C17E-5771-E58333072A1E";
	setAttr ".b" -type "string" "playbackOptions -min 0 -max 24 -ast 0 -aet 24 ";
	setAttr ".st" 6;
select -ne :time1;
	setAttr -av -k on ".cch";
	setAttr -k on ".fzn";
	setAttr -av -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr ".o" 1;
	setAttr -av -k on ".unw" 1;
	setAttr -av -k on ".etw";
	setAttr -av -k on ".tps";
	setAttr -av -k on ".tms";
select -ne :hardwareRenderingGlobals;
	setAttr -av -k on ".cch";
	setAttr -av -k on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr ".otfna" -type "stringArray" 22 "NURBS Curves" "NURBS Surfaces" "Polygons" "Subdiv Surface" "Particles" "Particle Instance" "Fluids" "Strokes" "Image Planes" "UI" "Lights" "Cameras" "Locators" "Joints" "IK Handles" "Deformers" "Motion Trails" "Components" "Hair Systems" "Follicles" "Misc. UI" "Ornaments"  ;
	setAttr ".otfva" -type "Int32Array" 22 0 1 1 1 1 1
		 1 1 1 0 0 0 0 0 0 0 0 0
		 0 0 0 0 ;
	setAttr -k on ".hwi";
	setAttr -av ".ta";
	setAttr -av ".tq";
	setAttr -av ".etmr";
	setAttr -av ".tmr";
	setAttr -av ".aoon";
	setAttr -av ".aoam";
	setAttr -av ".aora";
	setAttr -k on ".hff";
	setAttr -av ".hfd";
	setAttr -av -k on ".hfs";
	setAttr -av ".hfe";
	setAttr -av ".hfc";
	setAttr -av -k on ".hfcr";
	setAttr -av -k on ".hfcg";
	setAttr -av -k on ".hfcb";
	setAttr -av ".hfa";
	setAttr -av ".mbe";
	setAttr -av -k on ".mbsof";
	setAttr -k on ".blen";
	setAttr -k on ".blat";
	setAttr -av ".msaa";
	setAttr ".laa" yes;
	setAttr ".fprt" yes;
select -ne :renderPartition;
	setAttr -av -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -s 2 ".st";
	setAttr -cb on ".an";
	setAttr -cb on ".pt";
select -ne :renderGlobalsList1;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
select -ne :defaultShaderList1;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -s 4 ".s";
select -ne :postProcessList1;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -s 2 ".p";
select -ne :defaultRenderingList1;
	setAttr -k on ".ihi";
select -ne :initialShadingGroup;
	setAttr -av -k on ".cch";
	setAttr -k on ".fzn";
	setAttr -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -k on ".bbx";
	setAttr -k on ".vwm";
	setAttr -k on ".tpv";
	setAttr -k on ".uit";
	setAttr -k on ".mwc";
	setAttr -cb on ".an";
	setAttr -cb on ".il";
	setAttr -cb on ".vo";
	setAttr -cb on ".eo";
	setAttr -cb on ".fo";
	setAttr -cb on ".epo";
	setAttr ".ro" yes;
	setAttr -k on ".ai_surface_shader";
	setAttr -k on ".ai_volume_shader";
select -ne :initialParticleSE;
	setAttr -av -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -k on ".mwc";
	setAttr -cb on ".an";
	setAttr -cb on ".il";
	setAttr -cb on ".vo";
	setAttr -cb on ".eo";
	setAttr -cb on ".fo";
	setAttr -cb on ".epo";
	setAttr ".ro" yes;
	setAttr -k on ".ai_surface_shader";
	setAttr -k on ".ai_volume_shader";
select -ne :defaultRenderGlobals;
	setAttr -av -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -av -k on ".macc";
	setAttr -av -k on ".macd";
	setAttr -av -k on ".macq";
	setAttr -av ".mcfr";
	setAttr -cb on ".ifg";
	setAttr -av -k on ".clip";
	setAttr -av -k on ".edm";
	setAttr -av -k on ".edl";
	setAttr -av ".ren" -type "string" "arnold";
	setAttr -av -k on ".esr";
	setAttr -av -k on ".ors";
	setAttr -cb on ".sdf";
	setAttr -av -k on ".outf";
	setAttr -av -cb on ".imfkey";
	setAttr -av -k on ".gama";
	setAttr -k on ".exrc";
	setAttr -k on ".expt";
	setAttr -av -k on ".an";
	setAttr -cb on ".ar";
	setAttr -av ".fs";
	setAttr -av ".ef";
	setAttr -av -k on ".bfs";
	setAttr -cb on ".me";
	setAttr -cb on ".se";
	setAttr -av -k on ".be";
	setAttr -av -cb on ".ep";
	setAttr -av -k on ".fec";
	setAttr -av -k on ".ofc";
	setAttr -cb on ".ofe";
	setAttr -cb on ".efe";
	setAttr -cb on ".oft";
	setAttr -cb on ".umfn";
	setAttr -cb on ".ufe";
	setAttr -av -cb on ".pff";
	setAttr -av -k on ".peie";
	setAttr -av -cb on ".ifp";
	setAttr -k on ".rv";
	setAttr -av -k on ".comp";
	setAttr -av -k on ".cth";
	setAttr -av -k on ".soll";
	setAttr -cb on ".sosl";
	setAttr -av -k on ".rd";
	setAttr -av -k on ".lp";
	setAttr -av -k on ".sp";
	setAttr -av -k on ".shs";
	setAttr -av -k on ".lpr";
	setAttr -cb on ".gv";
	setAttr -cb on ".sv";
	setAttr -av -k on ".mm";
	setAttr -av -k on ".npu";
	setAttr -av -k on ".itf";
	setAttr -av -k on ".shp";
	setAttr -cb on ".isp";
	setAttr -av -k on ".uf";
	setAttr -av -k on ".oi";
	setAttr -av -k on ".rut";
	setAttr -av -k on ".mot";
	setAttr -av -cb on ".mb";
	setAttr -av -k on ".mbf";
	setAttr -av -k on ".mbso";
	setAttr -av -k on ".mbsc";
	setAttr -av -k on ".afp";
	setAttr -av -k on ".pfb";
	setAttr -av -k on ".pram";
	setAttr -av -k on ".poam";
	setAttr -av -k on ".prlm";
	setAttr -av -k on ".polm";
	setAttr -av -cb on ".prm";
	setAttr -av -cb on ".pom";
	setAttr -cb on ".pfrm";
	setAttr -cb on ".pfom";
	setAttr -av -k on ".bll";
	setAttr -av -k on ".bls";
	setAttr -av -k on ".smv";
	setAttr -av -k on ".ubc";
	setAttr -av -k on ".mbc";
	setAttr -cb on ".mbt";
	setAttr -av -k on ".udbx";
	setAttr -av -k on ".smc";
	setAttr -av -k on ".kmv";
	setAttr -cb on ".isl";
	setAttr -cb on ".ism";
	setAttr -cb on ".imb";
	setAttr -av -k on ".rlen";
	setAttr -av -k on ".frts";
	setAttr -av -k on ".tlwd";
	setAttr -av -k on ".tlht";
	setAttr -av -k on ".jfc";
	setAttr -cb on ".rsb";
	setAttr -av -k on ".ope";
	setAttr -av -k on ".oppf";
	setAttr -av -k on ".rcp";
	setAttr -av -k on ".icp";
	setAttr -av -k on ".ocp";
	setAttr -cb on ".hbl";
select -ne :defaultResolution;
	setAttr -av -k on ".cch";
	setAttr -av -k on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -k on ".bnm";
	setAttr -av -k on ".w";
	setAttr -av -k on ".h";
	setAttr -av ".pa" 1;
	setAttr -av -k on ".al";
	setAttr -av -k on ".dar";
	setAttr -av -k on ".ldar";
	setAttr -av -k on ".dpi";
	setAttr -av -k on ".off";
	setAttr -av -k on ".fld";
	setAttr -av -k on ".zsl";
	setAttr -av -k on ".isu";
	setAttr -av -k on ".pdu";
select -ne :hardwareRenderGlobals;
	setAttr -av -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -av ".ctrs" 256;
	setAttr -av ".btrs" 512;
	setAttr -av -k off -cb on ".fbfm";
	setAttr -av -k off -cb on ".ehql";
	setAttr -av -k off -cb on ".eams";
	setAttr -av -k off -cb on ".eeaa";
	setAttr -av -k off -cb on ".engm";
	setAttr -av -k off -cb on ".mes";
	setAttr -av -k off -cb on ".emb";
	setAttr -av -k off -cb on ".mbbf";
	setAttr -av -k off -cb on ".mbs";
	setAttr -av -k off -cb on ".trm";
	setAttr -av -k off -cb on ".tshc";
	setAttr -av -k off -cb on ".enpt";
	setAttr -av -k off -cb on ".clmt";
	setAttr -av -k off -cb on ".tcov";
	setAttr -av -k off -cb on ".lith";
	setAttr -av -k off -cb on ".sobc";
	setAttr -av -k off -cb on ".cuth";
	setAttr -av -k off -cb on ".hgcd";
	setAttr -av -k off -cb on ".hgci";
	setAttr -av -k off -cb on ".mgcs";
	setAttr -av -k off -cb on ".twa";
	setAttr -av -k off -cb on ".twz";
	setAttr -cb on ".hwcc";
	setAttr -cb on ".hwdp";
	setAttr -cb on ".hwql";
	setAttr -k on ".hwfr";
	setAttr -k on ".soll";
	setAttr -k on ".sosl";
	setAttr -k on ".bswa";
	setAttr -k on ".shml";
	setAttr -k on ".hwel";
relationship "link" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "link" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
connectAttr "layerManager.dli[0]" "defaultLayer.id";
connectAttr "renderLayerManager.rlmi[0]" "defaultRenderLayer.rlid";
connectAttr "defaultRenderLayer.msg" ":defaultRenderingList1.r" -na;
connectAttr "sliding_surfaceShape.iog" ":initialShadingGroup.dsm" -na;
// End of surface.ma
