extends Node3D

var player: CharacterBody3D
var camera: Camera3D
var crystals := 0
var health := 100.0
var hud: Label
var status: Label
var save_path := "user://frontier_save.json"

func _ready():
    _build_world()
    _build_player()
    _build_camera()
    _build_ui()
    _load_progress()

func mat(color: Color, roughness := 0.8) -> StandardMaterial3D:
    var m=StandardMaterial3D.new()
    m.albedo_color=color
    m.roughness=roughness
    return m

func mesh_box(size: Vector3, color: Color) -> MeshInstance3D:
    var n=MeshInstance3D.new()
    var b=BoxMesh.new()
    b.size=size
    n.mesh=b
    n.material_override=mat(color)
    return n

func mesh_sphere(radius: float, color: Color) -> MeshInstance3D:
    var n=MeshInstance3D.new()
    var s=SphereMesh.new()
    s.radius=radius
    s.height=radius*2.0
    n.mesh=s
    n.material_override=mat(color)
    return n

func _build_world():
    var env=WorldEnvironment.new()
    var e=Environment.new()
    e.background_mode=Environment.BG_COLOR
    e.background_color=Color(0.04,0.07,0.11)
    e.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
    e.ambient_light_color=Color(0.48,0.58,0.72)
    e.ambient_light_energy=0.75
    e.tonemap_mode=Environment.TONE_MAPPER_FILMIC
    env.environment=e
    add_child(env)

    var sun=DirectionalLight3D.new()
    sun.rotation_degrees=Vector3(-48,-28,0)
    sun.light_energy=1.25
    sun.shadow_enabled=true
    add_child(sun)

    var ground=mesh_box(Vector3(70,1,70),Color(0.16,0.24,0.20))
    ground.position.y=-0.5
    add_child(ground)

    for i in range(28):
        var x=float((i*17)%60)-30.0
        var z=float((i*31)%60)-30.0
        var h=2.0+float((i*7)%5)*0.65
        var rock=mesh_sphere(0.7+float(i%3)*0.25,Color(0.20,0.25,0.27))
        rock.scale=Vector3(1.2,h/1.5,1.0)
        rock.position=Vector3(x,h/2.0,z)
        add_child(rock)

    for i in range(12):
        var x=float((i*23)%50)-25.0
        var z=float((i*11)%50)-25.0
        var trunk=mesh_box(Vector3(0.45,2.4,0.45),Color(0.25,0.13,0.07))
        trunk.position=Vector3(x,1.2,z)
        add_child(trunk)
        var crown=mesh_sphere(1.5,Color(0.08,0.30,0.18))
        crown.position=Vector3(x,2.9,z)
        add_child(crown)

    for i in range(10):
        var x=float((i*19)%46)-23.0
        var z=float((i*29)%46)-23.0
        _spawn_crystal(Vector3(x,0.75,z))

    for i in range(4):
        _spawn_enemy(Vector3(-15+i*10,0.9,8-i*7))

func _spawn_crystal(pos: Vector3):
    var a=Area3D.new()
    a.position=pos
    a.set_meta("type","crystal")
    var c=CollisionShape3D.new()
    var shape=SphereShape3D.new()
    shape.radius=1.0
    c.shape=shape
    a.add_child(c)
    var visual=mesh_sphere(0.45,Color(0.18,0.85,1.0))
    visual.scale=Vector3(0.65,1.5,0.65)
    a.add_child(visual)
    a.body_entered.connect(_on_crystal_body.bind(a))
    add_child(a)

func _on_crystal_body(body, crystal):
    if body==player:
        crystals+=1
        crystal.queue_free()
        _update_hud()
        _save_progress()

func _spawn_enemy(pos: Vector3):
    var enemy=Node3D.new()
    enemy.position=pos
    enemy.set_meta("origin",pos)
    enemy.set_meta("phase",randf()*6.28)
    var body=mesh_box(Vector3(1.2,1.2,1.2),Color(0.75,0.18,0.20))
    body.position.y=0.6
    enemy.add_child(body)
    var eye=mesh_sphere(0.25,Color(1.0,0.75,0.2))
    eye.position=Vector3(0,0.8,0.65)
    enemy.add_child(eye)
    add_child(enemy)

func _build_player():
    player=CharacterBody3D.new()
    player.position=Vector3(0,1,0)
    var collision=CollisionShape3D.new()
    var capsule=CapsuleShape3D.new()
    capsule.radius=0.45
    capsule.height=1.8
    collision.shape=capsule
    player.add_child(collision)
    var body=mesh_box(Vector3(0.8,1.2,0.6),Color(0.16,0.42,0.75))
    body.position.y=0.1
    player.add_child(body)
    var head=mesh_sphere(0.38,Color(0.82,0.62,0.46))
    head.position.y=0.9
    player.add_child(head)
    add_child(player)

func _build_camera():
    camera=Camera3D.new()
    camera.position=Vector3(0,5.8,8.5)
    camera.rotation_degrees=Vector3(-28,0,0)
    add_child(camera)
    camera.current=true

func _physics_process(delta):
    if not player: return
    var input=Input.get_vector("move_left","move_right","move_forward","move_back")
    var dir=Vector3(input.x,0,input.y)
    if dir.length()>0.05:
        dir=dir.normalized()
        player.velocity.x=dir.x*7.0
        player.velocity.z=dir.z*7.0
        player.rotation.y=lerp_angle(player.rotation.y,atan2(-dir.x,-dir.z),delta*8.0)
    else:
        player.velocity.x=move_toward(player.velocity.x,0,28*delta)
        player.velocity.z=move_toward(player.velocity.z,0,28*delta)
    player.velocity.y=-4.0
    player.move_and_slide()

    var target=player.global_position+Vector3(0,0.8,0)
    camera.global_position=camera.global_position.lerp(target+Vector3(0,5.8,8.5),delta*5.0)
    camera.look_at(target,Vector3.UP)

    for enemy in get_children():
        if enemy is Node3D and enemy.has_meta("origin"):
            var origin:Vector3=enemy.get_meta("origin")
            var phase:float=enemy.get_meta("phase")
            enemy.position.x=origin.x+sin(Time.get_ticks_msec()*0.001+phase)*2.2
            enemy.position.z=origin.z+cos(Time.get_ticks_msec()*0.0012+phase)*1.6

    _update_hud()

func _build_ui():
    var layer=CanvasLayer.new()
    add_child(layer)
    hud=Label.new()
    hud.position=Vector2(28,24)
    hud.add_theme_font_size_override("font_size",28)
    layer.add_child(hud)
    status=Label.new()
    status.position=Vector2(28,68)
    status.add_theme_font_size_override("font_size",18)
    status.text="EXPLORE  •  COLLECT  •  SURVIVE"
    layer.add_child(status)
    _update_hud()

func _update_hud():
    if hud:
        hud.text="ENERGY  %d    HEALTH  %d%%" % [crystals,health]

func _save_progress():
    var f=FileAccess.open(save_path,FileAccess.WRITE)
    if f:
        f.store_string(JSON.stringify({"crystals":crystals,"health":health}))

func _load_progress():
    if not FileAccess.file_exists(save_path): return
    var f=FileAccess.open(save_path,FileAccess.READ)
    if f:
        var d=JSON.parse_string(f.get_as_text())
        if typeof(d)==TYPE_DICTIONARY:
            crystals=int(d.get("crystals",0))
            health=float(d.get("health",100))
