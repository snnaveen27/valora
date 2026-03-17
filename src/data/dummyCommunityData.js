/**
 * Centralized Dummy Data for Community Hub - Extended Bengaluru Localities
 * 
 * TO REMOVE LATER: Search for "is_dummy: true" or "source: 'demo'"
 * 
 * Covers 24 localities: 12 core + 12 outskirts/emerging
 */

// Core 12 + Outskirts 12 = 24 total
export const LOCALITIES = [
  // Core (Top 12 from BUSINESS.md)
  'whitefield','sarjapur_road','electronic_city','hsr_layout',
  'koramangala','indiranagar','bellandur','marathahalli',
  'hebbal','yelahanka','jp_nagar','kanakapura_road',
  // Outskirts & Emerging
  'mysore_road','bannerghatta_road','south_bangalore','yelahanka_new_town',
  'north_bangalore','hebbal_kempapura','jakkur','devanahalli',
  'tumkur_road','hennur','kr_puram','_old_airport_road',
];

export const LOCALITY_DISPLAY_NAMES = {
  // Core 12
  whitefield:'Whitefield',sarjapur_road:'Sarjapur Road',electronic_city:'Electronic City',
  hsr_layout:'HSR Layout',koramangala:'Koramangala',indiranagar:'Indiranagar',
  bellandur:'Bellandur',marathahalli:'Marathahalli',hebbal:'Hebbal',
  yelahanka:'Yelahanka',jp_nagar:'JP Nagar',kanakapura_road:'Kanakapura Road',
  // Outskirts
  mysore_road:'Mysore Road',bannerghatta_road:'Bannerghatta Road',south_bangalore:'South Bangalore',
  yelahanka_new_town:'Yelahanka New Town',north_bangalore:'North Bangalore',hebbal_kempapura:'Hebbal Kempapura',
  jakkur:'Jakkur',devanahalli:'Devanahalli',tumkur_road:'Tumkur Road',hennur:'Hennur',
  kr_puram:'KR Puram',old_airport_road:'Old Airport Road',
};

// Full data for 24 localities
export const DUMMY_DATA = {
  // ==================== CORE 12 ====================
  whitefield: {
    name: 'Whitefield',
    city: 'Bangalore',
    state: 'Karnataka',
    coordinates: { lat: 13.001, lng: 77.759 },
    reviews: [
      { id:'wf1', author_name:'Rahul Sharma', overall_rating:5, verification_type:'resident', title:'Excellent for families', content:'ORR connectivity, tech parks, schools nearby. Metro expected 2026.', helpful_count:24, created_at:'2026-02-15T10:30:00Z', is_verified:1, is_dummy:true, source:'demo' },
      { id:'wf2', author_name:'Sneha Iyer', overall_rating:4, verification_type:'owner', title:'Great ROI but traffic', content:'2BHK owner. 10% appreciation. Peak hour traffic is bad.', helpful_count:18, created_at:'2026-02-10T14:20:00Z', is_verified:1, is_dummy:true, source:'demo' },
      { id:'wf3', author_name:'Vijay Kumar', overall_rating:4, verification_type:'resident', title:'IT hub living', content:'Work at Accenture. Commute 20 min. Good cafes.', helpful_count:12, created_at:'2026-02-05T09:15:00Z', is_verified:1, is_dummy:true, source:'demo' },
      { id:'wf4', author_name:'Anjali Rao', overall_rating:5, verification_type:'owner', title:'Premium lifestyle', content:'3BHK in Brookfield. Excellent maintenance. Clubhouse and pool.', helpful_count:15, created_at:'2026-01-28T16:45:00Z', is_verified:1, is_dummy:true, source:'demo' },
    ],
    stats: { tr:127,vr:89,or:4.3,lr:4.2,cr:4.5,ar:4.1,sr:4.4,vr_r:3.8,wa_r:4.0,ps_r:4.2,is_dummy:true,source:'demo' },
    sentiment: { os:78,sl:'Positive',cf:85,ss:1250,ct:82,am:75,sf:80,if:76,lf:78,ch1:2.5,ch3:5.8,ch6:8.2,poi:45,tp:12,sc:8,hosp:5,is_dummy:true,source:'demo' },
    investment: { is:74,rl:'Low-Medium',a1:9.2,a3:28.5,a5:52.3,ry:4.8,rd:'High',sd:0.85,mp:'Growth',it_park:15,corp_office:45,is_dummy:true,source:'demo' },
    price: { cps:8500,pc1:1.2,pc3:3.8,pc1y:9.2,t:'Upward',min:4500,max:15000,avg:8500,apts:342,villas:28,plots:15,is_dummy:true,source:'demo' },
    demographics: { pop:85000,fam:22000,avg_inc:125000,tenancy:68,owner:32,is_dummy:true,source:'demo' },
    infrastructure: { metro:1,rail:0,bus:25,mall:4,hospital:5,school:12,park:8,lake:0,is_dummy:true,source:'demo' },
  },
  sarjapur_road: {
    name: 'Sarjapur Road',
    city: 'Bangalore',
    state: 'Karnataka',
    coordinates: { lat: 12.917, lng: 77.785 },
    reviews: [
      { id:'sr1', author_name:'Priya Patel', overall_rating:4, verification_type:'owner', title:'Great investment potential', content:'3BHK. Rapid development. 8-10% annual appreciation.', helpful_count:18, created_at:'2026-02-12T11:00:00Z', is_verified:1, is_dummy:true, source:'demo' },
      { id:'sr2', author_name:'Vikram Joshi', overall_rating:5, verification_type:'resident', title:'Perfect for young families', content:'Everything nearby. Upcoming metro = game changer.', helpful_count:22, created_at:'2026-02-08T15:30:00Z', is_verified:1, is_dummy:true, source:'demo' },
      { id:'sr3', author_name:'Arun Menon', overall_rating:4, verification_type:'resident', title:'Good connectivity', content:'Wipro SEZ 3km. Many rent options. Road widening ongoing.', helpful_count:14, created_at:'2026-02-03T10:20:00Z', is_verified:1, is_dummy:true, source:'demo' },
      { id:'sr4', author_name:'Meera Singh', overall_rating:4, verification_type:'owner', title:'Growing area', content:'Prestige Group project. Good amenities.', helpful_count:11, created_at:'2026-01-25T13:45:00Z', is_verified:1, is_dummy:true, source:'demo' },
    ],
    stats: { tr:98,vr:72,or:4.4,lr:4.3,cr:4.6,ar:4.2,sr:4.3,vr_r:4.0,wa_r:4.1,ps_r:4.3,is_dummy:true,source:'demo' },
    sentiment: { os:82,sl:'Very Positive',cf:88,ss:980,ct:78,am:80,sf:82,if:85,lf:82,ch1:3.2,ch3:7.1,ch6:12.5,poi:38,tp:8,sc:10,hosp:3,is_dummy:true,source:'demo' },
    investment: { is:82,rl:'Low',a1:12.5,a3:38.2,a5:68.5,ry:5.2,rd:'Very High',sd:0.75,mp:'Growth',it_park:12,corp_office:38,is_dummy:true,source:'demo' },
    price: { cps:7800,pc1:1.5,pc3:4.5,pc1y:12.5,t:'Upward',min:4200,max:14000,avg:7800,apts:285,villas:22,plots:18,is_dummy:true,source:'demo' },
    demo: { pop:72000,fam:18500,avg_inc:110000,tenancy:72,owner:28,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:18,mall:3,hospital:3,school:9,park:6,lake:0,is_dummy:true,source:'demo' },
  },
  hsr_layout: {
    reviews: [
      { id:'hsr1',n:'Anand Reddy',r:4,vt:'resident',t:'Perfect for IT professionals',c:'Supermarkets, restaurants, gyms, lake & parks.',hc:12,is_dummy:true,source:'demo' },
      { id:'hsr2',n:'Lakshmi Narayan',r:4,vt:'owner',t:'Well-planned layout',c:'Sector system makes navigation easy.',hc:15,is_dummy:true,source:'demo' },
      { id:'hsr3',n:'Karthik S',r:5,vt:'resident',t:'Best lifestyle area',c:'Lake view, jogging tracks, organic markets.',hc:20,is_dummy:true,source:'demo' },
      { id:'hsr4',n:'Divya P',r:3,vt:'visitor',t:'Traffic issues',c:'Sector 1 to 7 is huge.',hc:8,is_dummy:true,source:'demo' },
    ],
    stats: { tr:112,vr:85,or:4.2,lr:4.4,cr:4.3,ar:4.5,sr:4.1,vr_r:4.2,wa_r:4.3,ps_r:4.1,is_dummy:true,source:'demo' },
    sentiment: { os:76,sl:'Positive',cf:82,ss:890,ct:80,am:85,sf:75,if:72,lf:78,ch1:1.8,ch3:4.2,ch6:6.8,poi:52,tp:10,sc:14,hosp:4,is_dummy:true,source:'demo' },
    investment: { is:70,rl:'Low-Medium',a1:7.8,a3:24.5,a5:45.2,ry:4.5,rd:'High',sd:0.90,mp:'Mature',it_park:8,corp_office:25,is_dummy:true,source:'demo' },
    price: { cps:9200,pc1:0.8,pc3:2.5,pc1y:7.8,t:'Stable',min:5500,max:16500,avg:9200,apts:310,villas:35,plots:12,is_dummy:true,source:'demo' },
    demo: { pop:95000,fam:28000,avg_inc:135000,tenancy:62,owner:38,is_dummy:true,source:'demo' },
    infra: { metro:1,rail:0,bus:30,mall:5,hospital:4,school:15,park:12,lake:1,is_dummy:true,source:'demo' },
  },
  koramangala: {
    reviews: [
      { id:'ko1',n:'Rajesh Khanna',r:5,vt:'resident',t:'Heart of Bangalore',c:'Happening area. Excellent restaurants, pubs, malls.',hc:30,is_dummy:true,source:'demo' },
      { id:'ko2',n:'Neha Singh',r:4,vt:'owner',t:'Premium with great ROI',c:'4-5% rental yield. High corporate demand.',hc:20,is_dummy:true,source:'demo' },
      { id:'ko3',n:'Sanjay B',r:5,vt:'resident',t:'Startup hub',c:'Many startup offices. Great networking.',hc:25,is_dummy:true,source:'demo' },
      { id:'ko4',n:'Pooja Mehta',r:4,vt:'resident',t:'Youth area',c:'Lots of cafes, co-working spaces.',hc:18,is_dummy:true,source:'demo' },
    ],
    stats: { tr:156,vr:118,or:4.5,lr:4.5,cr:4.6,ar:4.7,sr:4.3,vr_r:4.5,wa_r:4.4,ps_r:4.5,is_dummy:true,source:'demo' },
    sentiment: { os:80,sl:'Very Positive',cf:90,ss:1100,ct:85,am:88,sf:78,if:80,lf:85,ch1:1.5,ch3:3.8,ch6:5.5,poi:65,tp:15,sc:18,hosp:6,is_dummy:true,source:'demo' },
    investment: { is:78,rl:'Low',a1:8.5,a3:26.8,a5:48.5,ry:4.2,rd:'Very High',sd:0.80,mp:'Mature',it_park:20,corp_office:55,is_dummy:true,source:'demo' },
    price: { cps:11000,pc1:0.6,pc3:2.2,pc1y:8.5,t:'Stable',min:6500,max:22000,avg:11000,apts:380,villas:42,plots:8,is_dummy:true,source:'demo' },
    demo: { pop:78000,fam:20000,avg_inc:145000,tenancy:58,owner:42,is_dummy:true,source:'demo' },
    infra: { metro:1,rail:1,bus:35,mall:7,hospital:6,school:12,park:5,lake:0,is_dummy:true,source:'demo' },
  },
  indiranagar: {
    reviews: [
      { id:'in1',n:'Arun Bhat',r:5,vt:'resident',t:'Classic Bangalore',c:'Great connectivity, amazing food, 100FT Road.',hc:25,is_dummy:true,source:'demo' },
      { id:'in2',n:'Smitha K',r:4,vt:'owner',t:'Bustling area',c:'Everything accessible. Little crowded but vibe great.',hc:16,is_dummy:true,source:'demo' },
    ],
    stats: { tr:89,vr:65,or:4.3,lr:4.4,cr:4.5,ar:4.3,sr:4.2,is_dummy:true,source:'demo' },
    sentiment: { os:77,sl:'Positive',cf:84,ss:750,ct:82,am:80,sf:75,if:74,lf:80,ch1:1.2,ch3:3.5,ch6:5.2,poi:48,tp:12,sc:10,hosp:5,is_dummy:true,source:'demo' },
    investment: { is:72,rl:'Low-Medium',a1:7.2,a3:22.5,a5:42.0,ry:4.6,rd:'High',sd:0.88,mp:'Mature',it_park:10,corp_office:30,is_dummy:true,source:'demo' },
    price: { cps:9800,pc1:0.5,pc3:1.8,pc1y:7.2,t:'Stable',min:5500,max:18000,avg:9800,apts:220,villas:28,plots:10,is_dummy:true,source:'demo' },
    demo: { pop:65000,fam:16000,avg_inc:120000,tenancy:65,owner:35,is_dummy:true,source:'demo' },
    infra: { metro:1,rail:0,bus:28,mall:4,hospital:5,school:8,park:6,lake:0,is_dummy:true,source:'demo' },
  },
  bellandur: {
    reviews: [
      { id:'be1',n:'Prakash Nair',r:4,vt:'resident',t:'Rapidly growing IT hub',c:'Largest IT hub. Massive development.',hc:16,is_dummy:true,source:'demo' },
      { id:'be2',n:'Reshma T',r:4,vt:'resident',t:'Many options',c:'Plenty of apartments. Easy commute to ORR.',hc:12,is_dummy:true,source:'demo' },
    ],
    stats: { tr:76,vr:52,or:4.1,lr:4.3,cr:4.2,ar:3.9,sr:4.0,is_dummy:true,source:'demo' },
    sentiment: { os:74,sl:'Positive',cf:80,ss:680,ct:78,am:72,sf:70,if:78,lf:75,ch1:2.1,ch3:5.0,ch6:8.8,poi:32,tp:6,sc:7,hosp:2,is_dummy:true,source:'demo' },
    investment: { is:76,rl:'Low-Medium',a1:10.2,a3:32.5,a5:58.0,ry:5.0,rd:'Very High',sd:0.72,mp:'Growth',it_park:18,corp_office:42,is_dummy:true,source:'demo' },
    price: { cps:7200,pc1:1.4,pc3:4.2,pc1y:10.2,t:'Upward',min:4000,max:12000,avg:7200,apts:195,villas:15,plots:22,is_dummy:true,source:'demo' },
    demo: { pop:58000,fam:14000,avg_inc:95000,tenancy:75,owner:25,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:15,mall:2,hospital:2,school:6,park:4,lake:1,is_dummy:true,source:'demo' },
  },
  marathahalli: {
    reviews: [
      { id:'ma1',n:'Suresh P',r:4,vt:'owner',t:'Great connectivity',c:'Near ORR & HAL. Construction delays.',hc:14,is_dummy:true,source:'demo' },
      { id:'ma2',n:'Sunita R',r:4,vt:'resident',t:'Affordable option',c:'Many budget PG options. Good for starters.',hc:11,is_dummy:true,source:'demo' },
    ],
    stats: { tr:58,vr:38,or:4.0,lr:4.3,cr:4.1,ar:3.8,sr:3.7,is_dummy:true,source:'demo' },
    sentiment: { os:72,sl:'Positive',cf:78,ss:520,ct:80,am:70,sf:68,if:72,lf:70,ch1:1.5,ch3:3.2,ch6:5.8,poi:28,tp:5,sc:5,hosp:3,is_dummy:true,source:'demo' },
    investment: { is:68,rl:'Medium',a1:6.5,a3:20.2,a5:38.5,ry:4.3,rd:'High',sd:0.92,mp:'Mature',it_park:8,corp_office:20,is_dummy:true,source:'demo' },
    price: { cps:6800,pc1:0.7,pc3:2.0,pc1y:6.5,t:'Stable',min:3800,max:11000,avg:6800,apts:150,villas:12,plots:8,is_dummy:true,source:'demo' },
    demo: { pop:45000,fam:11000,avg_inc:85000,tenancy:78,owner:22,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:20,mall:2,hospital:3,school:5,park:3,lake:0,is_dummy:true,source:'demo' },
  },
  hebbal: {
    reviews: [
      { id:'hb1',n:'Deepak Mehta',r:5,vt:'resident',t:'Premium lakeside living',c:'Hebbal Lake views. Excellent schools.',hc:28,is_dummy:true,source:'demo' },
      { id:'hb2',n:'Kavita Shetty',r:4,vt:'owner',t:'Excellent for luxury',c:'Villa. Peaceful, wide roads. Safe.',hc:19,is_dummy:true,source:'demo' },
    ],
    stats: { tr:84,vr:62,or:4.4,lr:4.2,cr:4.6,ar:4.4,sr:4.5,is_dummy:true,source:'demo' },
    sentiment: { os:81,sl:'Very Positive',cf:86,ss:620,ct:78,am:82,sf:85,if:80,lf:82,ch1:2.8,ch3:6.5,ch6:10.2,poi:35,tp:8,sc:8,hosp:4,is_dummy:true,source:'demo' },
    investment: { is:79,rl:'Low',a1:9.8,a3:30.5,a5:55.2,ry:4.7,rd:'High',sd:0.82,mp:'Growth',it_park:6,corp_office:18,is_dummy:true,source:'demo' },
    price: { cps:9500,pc1:1.1,pc3:3.5,pc1y:9.8,t:'Upward',min:5500,max:20000,avg:9500,apts:180,villas:32,plots:14,is_dummy:true,source:'demo' },
    demo: { pop:52000,fam:14000,avg_inc:115000,tenancy:60,owner:40,is_dummy:true,source:'demo' },
    infra: { metro:1,rail:1,bus:22,mall:3,hospital:4,school:8,park:5,lake:1,is_dummy:true,source:'demo' },
  },
  yelahanka: {
    reviews: [
      { id:'yl1',n:'Madhav Gupta',r:4,vt:'resident',t:'Peaceful suburb',c:'Close to airport. Good for travelers.',hc:12,is_dummy:true,source:'demo' },
      { id:'yl2',n:'Vasudha K',r:4,vt:'owner',t:'Old Bangalore charm',c:'Historical area. Many parks. Good schools.',hc:9,is_dummy:true,source:'demo' },
    ],
    stats: { tr:42,vr:28,or:3.9,lr:3.8,cr:4.0,ar:3.9,sr:4.1,is_dummy:true,source:'demo' },
    sentiment: { os:70,sl:'Positive',cf:75,ss:380,ct:65,am:70,sf:78,if:68,lf:72,ch1:1.0,ch3:2.5,ch6:4.2,poi:18,tp:4,sc:5,hosp:2,is_dummy:true,source:'demo' },
    investment: { is:65,rl:'Medium',a1:5.8,a3:18.5,a5:35.2,ry:4.0,rd:'Medium',sd:0.95,mp:'Emerging',it_park:2,corp_office:8,is_dummy:true,source:'demo' },
    price: { cps:5500,pc1:0.4,pc3:1.2,pc1y:5.8,t:'Stable',min:3200,max:9500,avg:5500,apts:95,villas:18,plots:25,is_dummy:true,source:'demo' },
    demo: { pop:35000,fam:10000,avg_inc:75000,tenancy:55,owner:45,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:1,bus:15,mall:1,hospital:2,school:4,park:4,lake:0,is_dummy:true,source:'demo' },
  },
  jp_nagar: {
    reviews: [
      { id:'jp1',n:'Radha Krishnan',r:4,vt:'resident',t:'Family-friendly South',c:'Well-established. Excellent schools.',hc:21,is_dummy:true,source:'demo' },
      { id:'jp2',n:'Vijay S',r:4,vt:'owner',t:'South Bangalore premium',c:'Good connectivity to Bannerghatta Road.',hc:16,is_dummy:true,source:'demo' },
    ],
    stats: { tr:105,vr:78,or:4.2,lr:4.1,cr:4.3,ar:4.4,sr:4.3,is_dummy:true,source:'demo' },
    sentiment: { os:75,sl:'Positive',cf:83,ss:820,ct:74,am:80,sf:78,if:72,lf:76,ch1:1.2,ch3:2.8,ch6:4.5,poi:40,tp:8,sc:12,hosp:4,is_dummy:true,source:'demo' },
    investment: { is:71,rl:'Low-Medium',a1:6.8,a3:21.2,a5:40.0,ry:4.4,rd:'High',sd:0.88,mp:'Mature',it_park:5,corp_office:22,is_dummy:true,source:'demo' },
    price: { cps:8800,pc1:0.5,pc3:1.6,pc1y:6.8,t:'Stable',min:4800,max:15000,avg:8800,apts:265,villas:30,plots:12,is_dummy:true,source:'demo' },
    demo: { pop:68000,fam:19000,avg_inc:105000,tenancy:58,owner:42,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:25,mall:4,hospital:4,school:10,park:8,lake:0,is_dummy:true,source:'demo' },
  },
  kanakapura_road: {
    reviews: [
      { id:'kp1',n:'Chetan S',r:4,vt:'owner',t:'Emerging corridor',c:'Many new projects. Quiet. Good for peace.',hc:10,is_dummy:true,source:'demo' },
      { id:'kp2',n:'Ramya H',r:4,vt:'resident',t:'Plotted development',c:'Own a plot. Away from city noise.',hc:8,is_dummy:true,source:'demo' },
    ],
    stats: { tr:38,vr:24,or:3.8,lr:3.6,cr:3.9,ar:3.7,sr:4.0,is_dummy:true,source:'demo' },
    sentiment: { os:69,sl:'Neutral to Positive',cf:72,ss:340,ct:60,am:65,sf:72,if:70,lf:68,ch1:1.5,ch3:3.2,ch6:5.8,poi:15,tp:3,sc:3,hosp:1,is_dummy:true,source:'demo' },
    investment: { is:66,rl:'Medium',a1:6.2,a3:19.5,a5:36.8,ry:4.1,rd:'Medium',sd:0.90,mp:'Emerging',it_park:1,corp_office:5,is_dummy:true,source:'demo' },
    price: { cps:5200,pc1:0.6,pc3:1.8,pc1y:6.2,t:'Stable',min:2800,max:8500,avg:5200,apts:85,villas:12,plots:35,is_dummy:true,source:'demo' },
    demo: { pop:28000,fam:7500,avg_inc:68000,tenancy:50,owner:50,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:10,mall:0,hospital:1,school:3,park:2,lake:0,is_dummy:true,source:'demo' },
  },
  electronic_city: {
    reviews: [
      { id:'ec1',n:'Harish Kumar',r:4,vt:'resident',t:'IT Paradise',c:'Infosys/Wipro? Live here. Good apartments.',hc:17,is_dummy:true,source:'demo' },
      { id:'ec2',n:'Rashmi A',r:4,vt:'resident',t:'Campus life',c:'Many company campuses. Good PG options.',hc:14,is_dummy:true,source:'demo' },
    ],
    stats: { tr:52,vr:35,or:4.1,lr:4.4,cr:4.2,ar:3.9,sr:4.0,is_dummy:true,source:'demo' },
    sentiment: { os:73,sl:'Positive',cf:77,ss:450,ct:75,am:68,sf:72,if:76,lf:70,ch1:1.8,ch3:4.5,ch6:7.2,poi:22,tp:4,sc:4,hosp:2,is_dummy:true,source:'demo' },
    investment: { is:73,rl:'Low-Medium',a1:8.5,a3:27.0,a5:50.5,ry:5.3,rd:'Very High',sd:0.78,mp:'Growth',it_park:25,corp_office:50,is_dummy:true,source:'demo' },
    price: { cps:6200,pc1:1.0,pc3:3.0,pc1y:8.5,t:'Upward',min:3500,max:10000,avg:6200,apts:130,villas:10,plots:20,is_dummy:true,source:'demo' },
    demo: { pop:42000,fam:10000,avg_inc:88000,tenancy:80,owner:20,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:12,mall:1,hospital:2,school:4,park:3,lake:0,is_dummy:true,source:'demo' },
  },

  // ==================== OUTSKIRTS 12 ====================
  mysore_road: {
    reviews: [
      { id:'mr1',n:'Ravi Kumar',r:4,vt:'resident',t:'Outskirts charm',c:'Quiet area. Good for families. 15km from city.',hc:10,is_dummy:true,source:'demo' },
      { id:'mr2',n:'Asha M',r:3,vt:'resident',t:'Developing area',c:'Many new projects. Infrastructure improving.',hc:6,is_dummy:true,source:'demo' },
    ],
    stats: { tr:28,vr:18,or:3.7,lr:3.5,cr:3.6,ar:3.8,sr:4.0,is_dummy:true,source:'demo' },
    sentiment: { os:65,sl:'Neutral',cf:68,ss:180,ct:55,am:60,sf:72,if:65,lf:68,ch1:0.8,ch3:2.0,ch6:3.5,poi:12,tp:2,sc:3,hosp:1,is_dummy:true,source:'demo' },
    investment: { is:62,rl:'Medium',a1:5.2,a3:15.0,a5:28.0,ry:3.8,rd:'Medium',sd:0.92,mp:'Emerging',it_park:1,corp_office:3,is_dummy:true,source:'demo' },
    price: { cps:4800,pc1:0.5,pc3:1.2,pc1y:5.2,t:'Stable',min:2500,max:8000,avg:4800,apts:65,villas:10,plots:30,is_dummy:true,source:'demo' },
    demo: { pop:22000,fam:6000,avg_inc:65000,tenancy:45,owner:55,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:8,mall:0,hospital:1,school:3,park:2,lake:0,is_dummy:true,source:'demo' },
  },
  bannerghatta_road: {
    reviews: [
      { id:'br1',n:'Madhuri S',r:4,vt:'resident',t:'Near NICE Road',c:'Great connectivity via NICE Road. Many villa projects.',hc:12,is_dummy:true,source:'demo' },
      { id:'br2',n:'Siddharth',r:4,vt:'owner',t:'Close to hospitals',c:'Near Manipal Hospital. Good for medical tourism.',hc:8,is_dummy:true,source:'demo' },
    ],
    stats: { tr:35,vr:22,or:4.0,lr:3.8,cr:4.0,ar:4.2,sr:4.0,is_dummy:true,source:'demo' },
    sentiment: { os:72,sl:'Positive',cf:74,ss:250,ct:70,am:72,sf:75,if:70,lf:74,ch1:1.2,ch3:3.0,ch6:5.0,poi:20,tp:4,sc:5,hosp:3,is_dummy:true,source:'demo' },
    investment: { is:69,rl:'Medium',a1:6.5,a3:20.0,a5:38.0,ry:4.2,rd:'Medium',sd:0.85,mp:'Growing',it_park:3,corp_office:10,is_dummy:true,source:'demo' },
    price: { cps:7500,pc1:0.8,pc3:2.0,pc1y:6.5,t:'Upward',min:4000,max:13000,avg:7500,apts:120,villas:25,plots:18,is_dummy:true,source:'demo' },
    demo: { pop:38000,fam:10000,avg_inc:90000,tenancy:55,owner:45,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:15,mall:2,hospital:3,school:5,park:4,lake:0,is_dummy:true,source:'demo' },
  },
  hebbal_kempapura: {
    reviews: [
      { id:'hk1',n:'Vikram Gowda',r:4,vt:'resident',t:'Near Manyata Tech',c:'Close to Manyata Tech Park. Good for IT professionals.',hc:14,is_dummy:true,source:'demo' },
      { id:'hk2',n:'Lakshmi R',r:4,vt:'owner',t:'North Bangalore emerging',c:'New developments. Good investment potential.',hc:10,is_dummy:true,source:'demo' },
    ],
    stats: { tr:32,vr:20,or:4.1,lr:4.0,cr:4.2,ar:4.0,sr:4.2,is_dummy:true,source:'demo' },
    sentiment: { os:73,sl:'Positive',cf:75,ss:220,ct:72,am:70,sf:78,if:72,lf:75,ch1:1.5,ch3:3.5,ch6:6.0,poi:18,tp:3,sc:4,hosp:2,is_dummy:true,source:'demo' },
    investment: { is:71,rl:'Low-Medium',a1:7.5,a3:22.0,a5:42.0,ry:4.5,rd:'High',sd:0.82,mp:'Growing',it_park:5,corp_office:12,is_dummy:true,source:'demo' },
    price: { cps:7800,pc1:0.9,pc3:2.5,pc1y:7.5,t:'Upward',min:4200,max:12000,avg:7800,apts:145,villas:18,plots:15,is_dummy:true,source:'demo' },
    demo: { pop:35000,fam:9000,avg_inc:92000,tenancy:62,owner:38,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:12,mall:1,hospital:2,school:4,park:3,lake:0,is_dummy:true,source:'demo' },
  },
  jakkur: {
    reviews: [
      { id:'jk1',n:'Tejaswi P',r:4,vt:'resident',t:'Near airport',c:'Close to Kempegowda Airport. Good for flyers.',hc:11,is_dummy:true,source:'demo' },
      { id:'jk2',n:'Nagaraj',r:4,vt:'owner',t:'Aerocity emerging',c:'Near upcoming Aerocity. Good for investors.',hc:8,is_dummy:true,source:'demo' },
    ],
    stats: { tr:25,vr:15,or:3.9,lr:3.8,cr:4.0,ar:3.8,sr:4.0,is_dummy:true,source:'demo' },
    sentiment: { os:68,sl:'Neutral to Positive',cf:70,ss:150,ct:65,am:62,sf:72,if:68,lf:70,ch1:1.0,ch3:2.5,ch6:4.5,poi:10,tp:2,sc:2,hosp:1,is_dummy:true,source:'demo' },
    investment: { is:67,rl:'Medium',a1:6.0,a3:18.0,a5:35.0,ry:4.3,rd:'Medium',sd:0.88,mp:'Emerging',it_park:2,corp_office:5,is_dummy:true,source:'demo' },
    price: { cps:6500,pc1:0.7,pc3:1.8,pc1y:6.0,t:'Upward',min:3500,max:10000,avg:6500,apts:85,villas:12,plots:20,is_dummy:true,source:'demo' },
    demo: { pop:18000,fam:4500,avg_inc:78000,tenancy:50,owner:50,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:8,mall:0,hospital:1,school:2,park:2,lake:0,is_dummy:true,source:'demo' },
  },
  devanahalli: {
    reviews: [
      { id:'dv1',n:'Shashidhar',r:4,vt:'owner',t:'Airport city',c:'Near Kempegowda Airport. Upcoming IT hub.',hc:15,is_dummy:true,source:'demo' },
      { id:'dv2',n:'Bhaskar Raj',r:5,vt:'resident',t:'Future potential',c:'Many aerospace SEZ projects. Excellent long-term.',hc:18,is_dummy:true,source:'demo' },
    ],
    stats: { tr:30,vr:20,or:4.2,lr:4.0,cr:4.2,ar:4.0,sr:4.3,is_dummy:true,source:'demo' },
    sentiment: { os:70,sl:'Positive',cf:72,ss:200,ct:68,am:65,sf:75,if:72,lf:70,ch1:1.3,ch3:3.2,ch6:5.5,poi:14,tp:3,sc:3,hosp:2,is_dummy:true,source:'demo' },
    investment: { is:72,rl:'Low-Medium',a1:7.8,a3:24.0,a5:45.0,ry:4.4,rd:'High',sd:0.80,mp:'Growth',it_park:4,corp_office:8,is_dummy:true,source:'demo' },
    price: { cps:5800,pc1:1.0,pc3:2.8,pc1y:7.8,t:'Upward',min:3000,max:9500,avg:5800,apts:75,villas:15,plots:25,is_dummy:true,source:'demo' },
    demo: { pop:25000,fam:6500,avg_inc:72000,tenancy:52,owner:48,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:1,bus:10,mall:1,hospital:1,school:3,park:2,lake:0,is_dummy:true,source:'demo' },
  },
  hennur: {
    reviews: [
      { id:'hn1',n:'Gurudev',r:4,vt:'resident',t:'North Bangalore rising',c:'Good connectivity to Hebbal. Many new apartments.',hc:12,is_dummy:true,source:'demo' },
      { id:'hn2',n:'Spoorthi',r:3,vt:'resident',t:'Still developing',c:'Infrastructure not fully ready. But good prices.',hc:6,is_dummy:true,source:'demo' },
    ],
    stats: { tr:28,vr:16,or:3.8,lr:3.6,cr:3.8,ar:3.9,sr:4.0,is_dummy:true,source:'demo' },
    sentiment: { os:67,sl:'Neutral to Positive',cf:69,ss:160,ct:62,am:62,sf:70,if:68,lf:68,ch1:0.9,ch3:2.2,ch6:4.0,poi:12,tp:2,sc:3,hosp:1,is_dummy:true,source:'demo' },
    investment: { is:66,rl:'Medium',a1:5.8,a3:17.0,a5:32.0,ry:4.0,rd:'Medium',sd:0.90,mp:'Emerging',it_park:1,corp_office:4,is_dummy:true,source:'demo' },
    price: { cps:5500,pc1:0.6,pc3:1.5,pc1y:5.8,t:'Stable',min:3000,max:9000,avg:5500,apts:80,villas:10,plots:22,is_dummy:true,source:'demo' },
    demo: { pop:30000,fam:8000,avg_inc:75000,tenancy:58,owner:42,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:10,mall:1,hospital:1,school:3,park:2,lake:0,is_dummy:true,source:'demo' },
  },
  kr_puram: {
    reviews: [
      { id:'kr1',n:'Praveen B',r:4,vt:'resident',t:'IT corridor east',c:'Close to Manyata Tech Park. Good residential.',hc:14,is_dummy:true,source:'demo' },
      { id:'kr2',n:'Divya K',r:4,vt:'owner',t:'Metro connectivity',c:'Upcoming metro will boost. Good investment.',hc:10,is_dummy:true,source:'demo' },
    ],
    stats: { tr:40,vr:25,or:4.0,lr:3.9,cr:4.1,ar:3.9,sr:4.1,is_dummy:true,source:'demo' },
    sentiment: { os:71,sl:'Positive',cf:73,ss:280,ct:70,am:68,sf:72,if:72,lf:72,ch1:1.1,ch3:2.8,ch6:5.2,poi:22,tp:4,sc:5,hosp:2,is_dummy:true,source:'demo' },
    investment: { is:70,rl:'Low-Medium',a1:6.8,a3:21.0,a5:40.0,ry:4.3,rd:'High',sd:0.84,mp:'Growing',it_park:6,corp_office:15,is_dummy:true,source:'demo' },
    price: { cps:7000,pc1:0.8,pc3:2.2,pc1y:6.8,t:'Upward',min:3800,max:11500,avg:7000,apts:155,villas:14,plots:16,is_dummy:true,source:'demo' },
    demo: { pop:45000,fam:12000,avg_inc:88000,tenancy:65,owner:35,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:14,mall:2,hospital:2,school:5,park:3,lake:0,is_dummy:true,source:'demo' },
  },
  old_airport_road: {
    reviews: [
      { id:'oa1',n:'Colonel Raj',r:5,vt:'resident',t:'Premium locality',c:'Near HAL campus. Very clean and green area.',hc:20,is_dummy:true,source:'demo' },
      { id:'oa2',n:'Anupa',r:4,vt:'owner',t:'Near Old Airport',c:'Close to old airport. Good for frequent travelers.',hc:12,is_dummy:true,source:'demo' },
    ],
    stats: { tr:45,vr:32,or:4.4,lr:4.5,cr:4.3,ar:4.3,sr:4.5,is_dummy:true,source:'demo' },
    sentiment: { os:76,sl:'Positive',cf:80,ss:350,ct:78,am:76,sf:78,if:74,lf:78,ch1:1.0,ch3:2.5,ch6:4.8,poi:28,tp:6,sc:6,hosp:3,is_dummy:true,source:'demo' },
    investment: { is:73,rl:'Low-Medium',a1:7.0,a3:22.0,a5:42.0,ry:4.4,rd:'High',sd:0.86,mp:'Mature',it_park:5,corp_office:18,is_dummy:true,source:'demo' },
    price: { cps:9000,pc1:0.6,pc3:1.8,pc1y:7.0,t:'Stable',min:5000,max:16000,avg:9000,apts:180,villas:22,plots:10,is_dummy:true,source:'demo' },
    demo: { pop:42000,fam:11000,avg_inc:115000,tenancy:60,owner:40,is_dummy:true,source:'demo' },
    infra: { metro:1,rail:0,bus:20,mall:3,hospital:3,school:6,park:5,lake:0,is_dummy:true,source:'demo' },
  },
  south_bangalore: {
    reviews: [
      { id:'sb1',n:'Dr. Rao',r:4,vt:'resident',t:'Classic residential',c:'Old Bangalore charm. Excellent schools.',hc:16,is_dummy:true,source:'demo' },
      { id:'sb2',n:'Priya Ram',r:4,vt:'owner',t:'Banashankari area',c:'Near ISRO campus. Good for families.',hc:12,is_dummy:true,source:'demo' },
    ],
    stats: { tr:55,vr:40,or:4.1,lr:4.0,cr:4.2,ar:4.3,sr:4.2,is_dummy:true,source:'demo' },
    sentiment: { os:74,sl:'Positive',cf:78,ss:420,ct:72,am:76,sf:78,if:70,lf:76,ch1:0.8,ch3:2.0,ch6:3.8,poi:32,tp:6,sc:10,hosp:4,is_dummy:true,source:'demo' },
    investment: { is:68,rl:'Low-Medium',a1:5.5,a3:18.0,a5:35.0,ry:4.2,rd:'Medium',sd:0.90,mp:'Mature',it_park:2,corp_office:10,is_dummy:true,source:'demo' },
    price: { cps:8200,pc1:0.4,pc3:1.2,pc1y:5.5,t:'Stable',min:4500,max:14000,avg:8200,apts:210,villas:28,plots:12,is_dummy:true,source:'demo' },
    demo: { pop:55000,fam:16000,avg_inc:100000,tenancy:55,owner:45,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:25,mall:3,hospital:4,school:10,park:6,lake:0,is_dummy:true,source:'demo' },
  },
  yelahanka_new_town: {
    reviews: [
      { id:'yn1',n:'Major Singh',r:4,vt:'resident',t:'Defence area',c:'Many defence quarters. Very safe. Green.',hc:14,is_dummy:true,source:'demo' },
      { id:'yn2',n:'Kavitha',r:4,vt:'owner',t:'Planned layout',c:'Well-planned. Near Yelahanka old town.',hc:10,is_dummy:true,source:'demo' },
    ],
    stats: { tr:22,vr:15,or:4.0,lr:3.9,cr:4.0,ar:4.1,sr:4.2,is_dummy:true,source:'demo' },
    sentiment: { os:69,sl:'Positive',cf:72,ss:140,ct:62,am:68,sf:76,if:66,lf:70,ch1:0.7,ch3:1.8,ch6:3.2,poi:10,tp:2,sc:3,hosp:1,is_dummy:true,source:'demo' },
    investment: { is:63,rl:'Medium',a1:5.0,a3:15.0,a5:30.0,ry:3.9,rd:'Medium',sd:0.94,mp:'Emerging',it_park:0,corp_office:3,is_dummy:true,source:'demo' },
    price: { cps:5200,pc1:0.4,pc3:1.0,pc1y:5.0,t:'Stable',min:2800,max:8500,avg:5200,apts:55,villas:12,plots:20,is_dummy:true,source:'demo' },
    demo: { pop:18000,fam:5000,avg_inc:70000,tenancy:48,owner:52,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:8,mall:0,hospital:1,school:2,park:3,lake:0,is_dummy:true,source:'demo' },
  },
  north_bangalore: {
    reviews: [
      { id:'nb1',n:'Mahesh D',r:4,vt:'resident',t:'Upcoming hub',c:'Many IT parks coming. Good future.',hc:12,is_dummy:true,source:'demo' },
      { id:'nb2',n:'Sandhya',r:3,vt:'resident',t:'Still growing',c:'Away from core city. Good for investment.',hc:8,is_dummy:true,source:'demo' },
    ],
    stats: { tr:35,vr:22,or:3.9,lr:3.8,cr:3.9,ar:4.0,sr:4.0,is_dummy:true,source:'demo' },
    sentiment: { os:68,sl:'Neutral to Positive',cf:70,ss:200,ct:65,am:65,sf:72,if:70,lf:68,ch1:1.0,ch3:2.5,ch6:4.5,poi:15,tp:3,sc:4,hosp:2,is_dummy:true,source:'demo' },
    investment: { is:68,rl:'Medium',a1:6.2,a3:19.0,a5:36.0,ry:4.1,rd:'Medium',sd:0.86,mp:'Growing',it_park:3,corp_office:8,is_dummy:true,source:'demo' },
    price: { cps:6000,pc1:0.7,pc3:1.8,pc1y:6.2,t:'Upward',min:3200,max:10000,avg:6000,apts:95,villas:14,plots:22,is_dummy:true,source:'demo' },
    demo: { pop:32000,fam:8500,avg_inc:80000,tenancy:55,owner:45,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:12,mall:1,hospital:2,school:4,park:3,lake:0,is_dummy:true,source:'demo' },
  },
  tumkur_road: {
    reviews: [
      { id:'tr1',n:'Venkatesh',r:4,vt:'owner',t:'Industrial area',c:'Near Tumkur highway. Good for industrial workers.',hc:10,is_dummy:true,source:'demo' },
      { id:'tr2',n:'Roopa',r:3,vt:'resident',t:'Outskirts',c:'Far from city. Good for budget buyers.',hc:6,is_dummy:true,source:'demo' },
    ],
    stats: { tr:20,vr:12,or:3.6,lr:3.4,cr:3.5,ar:3.7,sr:3.8,is_dummy:true,source:'demo' },
    sentiment: { os:62,sl:'Neutral',cf:65,ss:100,ct:50,am:55,sf:68,if:62,lf:65,ch1:0.5,ch3:1.2,ch6:2.5,poi:8,tp:1,sc:2,hosp:1,is_dummy:true,source:'demo' },
    investment: { is:60,rl:'Medium-High',a1:4.5,a3:12.0,a5:25.0,ry:3.5,rd:'Low',sd:0.95,mp:'Emerging',it_park:0,corp_office:2,is_dummy:true,source:'demo' },
    price: { cps:4200,pc1:0.3,pc3:0.8,pc1y:4.5,t:'Stable',min:2000,max:7000,avg:4200,apts:45,villas:8,plots:35,is_dummy:true,source:'demo' },
    demo: { pop:15000,fam:4000,avg_inc:55000,tenancy:40,owner:60,is_dummy:true,source:'demo' },
    infra: { metro:0,rail:0,bus:6,mall:0,hospital:0,school:2,park:1,lake:0,is_dummy:true,source:'demo' },
  },
};

// Extended decision rooms (16 total)
export const DUMMY_SESSIONS = [
  // Core
  { id:'s1',fn:'Sharma Family',tl:'whitefield',td:'Whitefield',st:'active',m:4,bm:15000000,pt:['apartment','villa'],is_dummy:true,source:'demo' },
  { id:'s2',fn:'Patel Group',tl:'sarjapur_road',td:'Sarjapur Road',st:'active',m:3,bm:20000000,pt:['apartment'],is_dummy:true,source:'demo' },
  { id:'s3',fn:'Reddy Family',tl:'hsr_layout',td:'HSR Layout',st:'active',m:5,bm:12000000,pt:['apartment','plot'],is_dummy:true,source:'demo' },
  { id:'s4',fn:'Kumar Family',tl:'koramangala',td:'Koramangala',st:'active',m:2,bm:18000000,pt:['apartment'],is_dummy:true,source:'demo' },
  { id:'s5',fn:'Mehta Investment',tl:'hebbal',td:'Hebbal',st:'active',m:2,bm:25000000,pt:['villa','penthouse'],is_dummy:true,source:'demo' },
  { id:'s6',fn:'Singh Family',tl:'indiranagar',td:'Indiranagar',st:'active',m:4,bm:22000000,pt:['apartment','villa'],is_dummy:true,source:'demo' },
  { id:'s7',fn:'Tech Pro Group',tl:'electronic_city',td:'Electronic City',st:'active',m:1,bm:8000000,pt:['apartment'],is_dummy:true,source:'demo' },
  { id:'s8',fn:'Agarwal Family',tl:'bellandur',td:'Bellandur',st:'active',m:3,bm:14000000,pt:['apartment'],is_dummy:true,source:'demo' },
  // Outskirts
  { id:'s9',fn:'Joshi Family',tl:'mysore_road',td:'Mysore Road',st:'active',m:3,bm:9000000,pt:['villa'],is_dummy:true,source:'demo' },
  { id:'s10',fn:'Rao Family',tl:'devanahalli',td:'Devanahalli',st:'active',m:4,bm:11000000,pt:['villa','plot'],is_dummy:true,source:'demo' },
  { id:'s11',fn:'Nair Group',tl:'kr_puram',td:'KR Puram',st:'active',m:2,bm:8500000,pt:['apartment'],is_dummy:true,source:'demo' },
  { id:'s12',fn:'Green Valley Trust',tl:'kanakapura_road',td:'Kanakapura Road',st:'active',m:5,bm:35000000,pt:['plot','villa'],is_dummy:true,source:'demo' },
  { id:'s13',fn:'Aerospace Team',tl:'hebbal_kempapura',td:'Hebbal Kempapura',st:'active',m:4,bm:18000000,pt:['apartment'],is_dummy:true,source:'demo' },
  { id:'s14',fn:'Airport Commuters',tl:'jakkur',td:'Jakkur',st:'active',m:2,bm:12000000,pt:['villa'],is_dummy:true,source:'demo' },
  { id:'s15',fn:'Bannerghatta Residents',tl:'bannerghatta_road',td:'Bannerghatta Road',st:'active',m:3,bm:14000000,pt:['villa','apartment'],is_dummy:true,source:'demo' },
  { id:'s16',fn:'Old Airport Group',tl:'old_airport_road',td:'Old Airport Road',st:'active',m:2,bm:16000000,pt:['apartment'],is_dummy:true,source:'demo' },
];

// Extended trending (12)
export const DUMMY_TRENDING = [
  { id:'sarjapur_road',n:'Sarjapur Road',s:82,c:7.1,ai:12.5,is_dummy:true,source:'demo' },
  { id:'hebbal',n:'Hebbal',s:81,c:6.5,ai:9.8,is_dummy:true,source:'demo' },
  { id:'whitefield',n:'Whitefield',s:78,c:5.8,ai:9.2,is_dummy:true,source:'demo' },
  { id:'koramangala',n:'Koramangala',s:80,c:3.8,ai:8.5,is_dummy:true,source:'demo' },
  { id:'bellandur',n:'Bellandur',s:74,c:5.0,ai:10.2,is_dummy:true,source:'demo' },
  { id:'devanahalli',n:'Devanahalli',s:72,c:3.2,ai:7.8,is_dummy:true,source:'demo' },
  { id:'kr_puram',n:'KR Puram',s:71,c:2.8,ai:6.8,is_dummy:true,source:'demo' },
  { id:'electronic_city',n:'Electronic City',s:73,c:4.5,ai:8.5,is_dummy:true,source:'demo' },
  { id:'hsr_layout',n:'HSR Layout',s:76,c:4.2,ai:7.8,is_dummy:true,source:'demo' },
  { id:'hebbal_kempapura',n:'Hebbal Kempapura',s:73,c:3.5,ai:7.5,is_dummy:true,source:'demo' },
  { id:'indiranagar',n:'Indiranagar',s:77,c:3.5,ai:7.2,is_dummy:true,source:'demo' },
  { id:'bannerghatta_road',n:'Bannerghatta Road',s:72,c:3.0,ai:6.5,is_dummy:true,source:'demo' },
];

// Extended activities (16)
export const DUMMY_ACTIVITIES = [
  { id:'a1',t:'price_increase',d:'Price +2.5% in Sarjapur Road',ts:'2026-03-05T10:30:00Z',l:'sarjapur_road',is_dummy:true,source:'demo' },
  { id:'a2',t:'new_listing',d:'15 new listings in Whitefield',ts:'2026-03-04T14:20:00Z',l:'whitefield',is_dummy:true,source:'demo' },
  { id:'a3',t:'market_update',d:'Rental demand +8% in HSR Layout',ts:'2026-03-03T09:15:00Z',l:'hsr_layout',is_dummy:true,source:'demo' },
  { id:'a4',t:'sentiment_rise',d:'Hebbal sentiment up to 81',ts:'2026-03-02T16:45:00Z',l:'hebbal',is_dummy:true,source:'demo' },
  { id:'a5',t:'new_review',d:'New verified review in Koramangala',ts:'2026-03-01T11:20:00Z',l:'koramangala',is_dummy:true,source:'demo' },
  { id:'a6',t:'investment',d:'Investment score upgraded for Electronic City',ts:'2026-02-28T14:30:00Z',l:'electronic_city',is_dummy:true,source:'demo' },
  { id:'a7',t:'price_increase',d:'Price +1.8% in Bellandur',ts:'2026-02-27T10:15:00Z',l:'bellandur',is_dummy:true,source:'demo' },
  { id:'a8',t:'new_session',d:'New decision room for JP Nagar buyers',ts:'2026-02-26T09:00:00Z',l:'jp_nagar',is_dummy:true,source:'demo' },
  { id:'a9',t:'metro',d:'Metro construction milestone in Whitefield',ts:'2026-02-25T15:30:00Z',l:'whitefield',is_dummy:true,source:'demo' },
  { id:'a10',t:'infrastructure',d:'Devanahalli IT SEZ expansion approved',ts:'2026-02-24T11:00:00Z',l:'devanahalli',is_dummy:true,source:'demo' },
  { id:'a11',t:'new_listing',d:'20 new villa projects in Hebbal',ts:'2026-02-23T13:45:00Z',l:'hebbal',is_dummy:true,source:'demo' },
  { id:'a12',t:'infrastructure',d:'Road widening complete in Marathahalli',ts:'2026-02-22T10:00:00Z',l:'marathahalli',is_dummy:true,source:'demo' },
  { id:'a13',t:'sentiment_rise',d:'KR Puram sentiment up 5%',ts:'2026-02-21T14:20:00Z',l:'kr_puram',is_dummy:true,source:'demo' },
  { id:'a14',t:'new_session',d:'New decision room for Devanahalli investors',ts:'2026-02-20T09:30:00Z',l:'devanahalli',is_dummy:true,source:'demo' },
  { id:'a15',t:'price_increase',d:'Price +1.5% in Bannerghatta Road',ts:'2026-02-19T11:00:00Z',l:'bannerghatta_road',is_dummy:true,source:'demo' },
  { id:'a16',t:'market_update',d:'New aerospace companies in Hebbal Kempapura',ts:'2026-02-18T16:00:00Z',l:'hebbal_kempapura',is_dummy:true,source:'demo' },
];

// Helpers
export const getLocalityData = (id) => {
  const n = (id||'').toLowerCase().trim().replace(/[^a-z0-9]/g,'_');
  return DUMMY_DATA[n] || DUMMY_DATA.whitefield;
};

export const getSessionsByLocality = (id) => {
  const n = (id||'').toLowerCase().trim().replace(/[^a-z0-9]/g,'_');
  return DUMMY_SESSIONS.filter(s=>s.tl===n);
};

export const isDummyData = (d) => d?.is_dummy===true || d?.source==='demo';

// getLocalityInfo - helper function to get locality details
export const getLocalityInfo = (localityId) => {
  const n = (localityId||'').toLowerCase().trim().replace(/[^a-z0-9]/g,'_');
  const data = DUMMY_DATA[n];
  if (!data) return null;
  return {
    id: n,
    name: LOCALITY_DISPLAY_NAMES[n] || n,
    stats: data.stats,
    sentiment: data.sentiment,
    investment: data.investment,
    price: data.price,
    demographics: data.demographics,
    infrastructure: data.infra,
  };
};

// Backwards-compatible exports for components expecting separate arrays
// Reviews are now nested inside DUMMY_DATA[locality].reviews
export const DUMMY_REVIEWS = DUMMY_DATA; // Full data object with reviews nested
export const DUMMY_REVIEW_STATS = Object.fromEntries(
  Object.entries(DUMMY_DATA).map(([key, val]) => [key, val.stats])
);
export const DUMMY_SENTIMENTS = Object.fromEntries(
  Object.entries(DUMMY_DATA).map(([key, val]) => [key, val.sentiment])
);
export const DUMMY_INVESTMENTS = Object.fromEntries(
  Object.entries(DUMMY_DATA).map(([key, val]) => [key, val.investment])
);
export const DUMMY_PRICE_DATA = Object.fromEntries(
  Object.entries(DUMMY_DATA).map(([key, val]) => [key, val.price])
);

export default { LOCALITIES,LOCALITY_DISPLAY_NAMES,DUMMY_DATA,DUMMY_SESSIONS,DUMMY_TRENDING,DUMMY_ACTIVITIES,getLocalityData,getSessionsByLocality,isDummyData,getLocalityInfo,DUMMY_REVIEWS,DUMMY_REVIEW_STATS,DUMMY_SENTIMENTS,DUMMY_INVESTMENTS,DUMMY_PRICE_DATA };
