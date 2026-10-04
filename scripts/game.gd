extends Node3D

var player: CharacterBody3D
var camera: Camera3D
var hud: Label
var status: Label
var action_label: Label
var crystals:=0
var health:=100.0
var level:=1
var xp:=0
var attack_cooldown:=0.0
var save_path:="user://frontier_save.json"
var enemies:Array[Node3D]=[]

func _ready():
 randomize(); _build_world(); _build_player(); _build_camera(); _build_ui(); _load_progress(); _update_hud()

func mat(c:Color,r:=0.8,e:=Color.BLACK)->StandardMaterial3D:
 var m=StandardMaterial3D.new(); m.albedo_color=c; m.roughness=r
 if e!=Color.BLACK: m.emission_enabled=true; m.emission=e; m.emission_energy_multiplier=1.8
 return m

func box(s:Vector3,c:Color)->MeshInstance3D:
 var n=MeshInstance3D.new(); var b=BoxMesh.new(); b.size=s; n.mesh=b; n.material_override=mat(c); return n

func sphere(r:float,c:Color,e:=Color.BLACK)->MeshInstance3D:
 var n=MeshInstance3D.new(); var s=SphereMesh.new(); s.radius=r; s.height=r*2; n.mesh=s; n.material_override=mat(c,0.55,e); return n

func _build_world():
 var env=WorldEnvironment.new(); var e=Environment.new(); e.background_mode=Environment.BG_COLOR; e.background_color=Color(0.025,0.045,0.075); e.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR; e.ambient_light_color=Color(0.52,0.62,0.76); e.ambient_light_energy=0.8; e.tonemap_mode=Environment.TONE_MAPPER_FILMIC; env.environment=e; add_child(env)
 var sun=DirectionalLight3D.new(); sun.rotation_degrees=Vector3(-52,-30,0); sun.light_energy=1.35; sun.shadow_enabled=true; add_child(sun)
 var ground=box(Vector3(80,1,80),Color(0.12,0.20,0.16)); ground.position.y=-0.5; add_child(ground)
 for i in range(36):
  var x=float((i*17)%70)-35.0; var z=float((i*31)%70)-35.0; var h=1.8+float((i*7)%5)*0.6
  var rock=sphere(0.65+float(i%3)*0.22,Color(0.19,0.24,0.27)); rock.scale=Vector3(1.2,h/1.4,1); rock.position=Vector3(x,h/2,z); add_child(rock)
 for i in range(16):
  var x=float((i*23)%60)-30.0; var z=float((i*11)%60)-30.0
  var trunk=box(Vector3(.42,2.5,.42),Color(.24,.12,.065)); trunk.position=Vector3(x,1.25,z); add_child(trunk)
  var crown=sphere(1.55,Color(.055,.26,.15)); crown.position=Vector3(x,2.95,z); add_child(crown)
 for i in range(14): _spawn_crystal(Vector3(float((i*19)%54)-27,.72,float((i*29)%54)-27))
 for i in range(6): _spawn_enemy(Vector3(-20+i*8,.8,10-i*5))

func _spawn_crystal(pos:Vector3):
 var a=Area3D.new(); a.position=pos
 var c=CollisionShape3D.new(); var sh=SphereShape3D.new(); sh.radius=1; c.shape=sh; a.add_child(c)
 var v=sphere(.45,Color(.10,.75,1),Color(.05,.55,1)); v.scale=Vector3(.65,1.55,.65); a.add_child(v)
 a.body_entered.connect(_on_crystal_body.bind(a)); add_child(a)

func _on_crystal_body(body,crystal):
 if body==player: crystals+=1; _gain_xp(10); crystal.queue_free(); status.text="ENERGY CRYSTAL COLLECTED"; _update_hud()

func _spawn_enemy(pos:Vector3):
 var enemy=Node3D.new(); enemy.position=pos; enemy.set_meta("origin",pos); enemy.set_meta("phase",randf()*6.28); enemy.set_meta("hp",3)
 var body=box(Vector3(1.15,1.2,1.15),Color(.62,.12,.16)); body.position.y=.6; enemy.add_child(body)
 var eye=sphere(.24,Color(1,.62,.08),Color(1,.2,.02)); eye.position=Vector3(0,.82,.64); enemy.add_child(eye)
 add_child(enemy); enemies.append(enemy)

func _build_player():
 player=CharacterBody3D.new(); player.position=Vector3(0,1,0)
 var col=CollisionShape3D.new(); var cap=CapsuleShape3D.new(); cap.radius=.45; cap.height=1.8; col.shape=cap; player.add_child(col)
 var body=box(Vector3(.78,1.2,.58),Color(.10,.36,.72)); body.position.y=.05; player.add_child(body)
 var head=sphere(.38,Color(.82,.62,.46)); head.position.y=.88; player.add_child(head)
 var core=sphere(.12,Color(.15,.9,1),Color(.1,.8,1)); core.position=Vector3(0,.15,-.34); player.add_child(core); add_child(player)

func _build_camera():
 camera=Camera3D.new(); camera.position=Vector3(0,5.8,8.5); add_child(camera); camera.current=true

func _physics_process(delta):
 if not player:return
 attack_cooldown=max(0.,attack_cooldown-delta)
 var input=Input.get_vector("move_left","move_right","move_forward","move_back"); var dir=Vector3(input.x,0,input.y)
 if dir.length()>.05:
  dir=dir.normalized(); player.velocity.x=dir.x*7; player.velocity.z=dir.z*7; player.rotation.y=lerp_angle(player.rotation.y,atan2(-dir.x,-dir.z),delta*9)
 else:
  player.velocity.x=move_toward(player.velocity.x,0,28*delta); player.velocity.z=move_toward(player.velocity.z,0,28*delta)
 player.velocity.y=-4; player.move_and_slide()
 var target=player.global_position+Vector3(0,.8,0); camera.global_position=camera.global_position.lerp(target+Vector3(0,5.8,8.5),delta*5); camera.look_at(target,Vector3.UP)
 for enemy in enemies.duplicate():
  if not is_instance_valid(enemy): enemies.erase(enemy); continue
  var origin:Vector3=enemy.get_meta("origin"); var phase:float=enemy.get_meta("phase")
  enemy.position.x=origin.x+sin(Time.get_ticks_msec()*.001+phase)*2.2; enemy.position.z=origin.z+cos(Time.get_ticks_msec()*.0012+phase)*1.6
  if enemy.position.distance_to(player.position)<1.65: health=max(0.,health-12*delta); if health<=0:_respawn()
 _update_hud()

func attack():
 if attack_cooldown>0:return
 attack_cooldown=.45
 for enemy in enemies.duplicate():
  if is_instance_valid(enemy) and enemy.position.distance_to(player.position)<3:
   var hp=int(enemy.get_meta("hp"))-1; enemy.set_meta("hp",hp)
   if hp<=0: enemies.erase(enemy); enemy.queue_free(); crystals+=2; _gain_xp(30); status.text="SENTRY DEFEATED  +2 ENERGY"
   else: status.text="HIT  •  %d HP REMAINING"%hp

func _input(event):
 if event is InputEventKey and event.pressed and event.keycode==KEY_SPACE: attack()
 if event is InputEventScreenTouch and event.pressed: attack()

func _respawn(): health=100; player.position=Vector3.ZERO; status.text="RECOVERED AT BASE"

func _gain_xp(amount:int):
 xp+=amount; var need=level*100
 if xp>=need: xp-=need; level+=1; health=min(100.,health+20); status.text="LEVEL UP  •  LEVEL %d"%level
 _save_progress()

func _build_ui():
 var layer=CanvasLayer.new(); add_child(layer)
 var panel=ColorRect.new(); panel.position=Vector2(18,18); panel.size=Vector2(440,108); panel.color=Color(.02,.04,.07,.78); layer.add_child(panel)
 hud=Label.new(); hud.position=Vector2(34,28); hud.add_theme_font_size_override("font_size",24); layer.add_child(hud)
 status=Label.new(); status.position=Vector2(34,78); status.add_theme_font_size_override("font_size",16); status.text="EXPLORE  •  COLLECT  •  SURVIVE"; layer.add_child(status)
 action_label=Label.new(); action_label.text="ATTACK  •  SPACE / TAP"; action_label.position=Vector2(1030,620); action_label.add_theme_font_size_override("font_size",18); layer.add_child(action_label)

func _update_hud():
 if hud: hud.text="ENERGY %02d    HP %03d    LV %02d    XP %03d"%[crystals,health,level,xp]

func _save_progress():
 var f=FileAccess.open(save_path,FileAccess.WRITE)
 if f:f.store_string(JSON.stringify({"crystals":crystals,"health":health,"level":level,"xp":xp}))

func _load_progress():
 if not FileAccess.file_exists(save_path):return
 var f=FileAccess.open(save_path,FileAccess.READ)
 if f:
  var d=JSON.parse_string(f.get_as_text())
  if typeof(d)==TYPE_DICTIONARY: crystals=int(d.get("crystals",0)); health=float(d.get("health",100)); level=int(d.get("level",1)); xp=int(d.get("xp",0))
