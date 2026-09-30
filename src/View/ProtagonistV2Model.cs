using System.Collections.Generic;
using System.Text.Json;
using Godot;

namespace Cidadela.View;

/// <summary>
/// Monta a protagonista v2 (docs/protagonista_v2_contrato.md) a partir de assets/modelos/protagonista_v2/: o corpo com os
/// clipes idle-loop e run-loop; a pele e o tecido no toon com a borda fria e o piso de sombra dela; o rosto
/// (<see cref="ProtagonistFace"/>); o cabelo com pesos ligado ao esqueleto do corpo pelos nomes dos ossos; os chifres no
/// encaixe "Chifres" (Head) e o cristal no "Peito" (Spine), os dois vindos no espaço do corpo em repouso; a luz azul do
/// cristal e a camada de render própria da v1; e os encaixes do contrato de animação. Cores e piso em data/castellan.json.
/// </summary>
public static class ProtagonistV2Model
{
    public const string Dir = "res://assets/modelos/protagonista_v2/";
    // No GLB são "idle-loop" e "run-loop"; o importador do Godot tira o sufixo "-loop" e liga o laço.
    public const string IdleClip = "idle", RunClip = "run";
    private const string RunClipInJson = "run-loop";

    public sealed record Built(Node3D Model, AnimationPlayer? Animations, ProtagonistFace Face, float RunStride);

    public static bool Available => ResourceLoader.Exists(Dir + "protagonista_corpo.glb");

    public static Built Build(Node3D parent, uint selfLayer)
    {
        Looks looks = ReadLooks();
        var model = GD.Load<PackedScene>(Dir + "protagonista_corpo.glb").Instantiate<Node3D>();
        model.Name = "ProtagonistaV2";
        model.RotationDegrees = new Vector3(0f, 180f, 0f); // frente do glTF em +Z; o Castelão olha para -Z
        parent.AddChild(model);

        Skeleton3D skeleton = First<Skeleton3D>(model)!;
        Transform3D skeletonInModel = Transform3D.Identity;
        for (Node n = skeleton; n != model && n is Node3D n3; n = n.GetParent())
            skeletonInModel = n3.Transform * skeletonInModel;

        MeshInstance3D? eyes = null, mouth = null;
        ShaderMaterial skin = Toon(looks.Skin, looks.ShadowFloor), cloth = Toon(looks.Cloth, looks.ShadowFloor);
        foreach (MeshInstance3D mesh in VillagerLooks.Descendants<MeshInstance3D>(model))
        {
            if (mesh.Name == "Olhos") { eyes = mesh; continue; }
            if (mesh.Name == "Boca") { mouth = mesh; continue; }
            mesh.MaterialOverride = mesh.Name == "roupa_intima" ? cloth : skin;
        }
        var face = new ProtagonistFace(eyes, mouth, looks.ShadowFloor);

        // Cabelo com pesos: a malha passa para o esqueleto do corpo; a pele liga os ossos pelo nome.
        var hairScene = GD.Load<PackedScene>(Dir + "cabelo.glb").Instantiate<Node3D>();
        if (First<MeshInstance3D>(hairScene) is MeshInstance3D hair)
        {
            hair.GetParent().RemoveChild(hair);
            hair.Owner = null;
            skeleton.AddChild(hair);
            hair.Transform = Transform3D.Identity;
            hair.Skeleton = hair.GetPathTo(skeleton);
            hair.MaterialOverride = Toon(looks.Hair, looks.ShadowFloor);
        }
        hairScene.QueueFree();

        Node3D? head = Socket(skeleton, skeletonInModel, "Head", "Chifres");
        Node3D? chest = Socket(skeleton, skeletonInModel, "Spine", "Peito");
        Socket(skeleton, skeletonInModel, "Head", "Cabelo");
        Socket(skeleton, skeletonInModel, "Head", "Chapéu");
        Socket(skeleton, skeletonInModel, "RightHand", "MaoDireita");
        Socket(skeleton, skeletonInModel, "LeftHand", "MaoEsquerda");
        Socket(skeleton, skeletonInModel, "Spine01", "Costas");

        if (head is not null && First<MeshInstance3D>(GD.Load<PackedScene>(Dir + "chifres.glb").Instantiate<Node3D>()) is MeshInstance3D horns)
        {
            Reparent(horns, head);
            horns.MaterialOverride = Toon(looks.Horn, looks.ShadowFloor);
        }
        if (chest is not null && First<MeshInstance3D>(GD.Load<PackedScene>(Dir + "cristal.glb").Instantiate<Node3D>()) is MeshInstance3D crystal)
        {
            Reparent(crystal, chest); // material "Cristal" do GLB: o único emissivo
            chest.AddChild(CrystalLight(selfLayer));
        }

        foreach (MeshInstance3D mesh in VillagerLooks.Descendants<MeshInstance3D>(model))
            mesh.Layers = selfLayer;

        AnimationPlayer? animations = First<AnimationPlayer>(model);
        if (animations is not null)
            foreach (string clip in new[] { IdleClip, RunClip })
                if (animations.HasAnimation(clip))
                    animations.GetAnimation(clip).LoopMode = Animation.LoopModeEnum.Linear;
        return new Built(model, animations, face, ReadStride());
    }

    /// <summary>Luz azul do cristal (valores da v1 gravados em cristal.json); não ilumina a própria protagonista.</summary>
    private static OmniLight3D CrystalLight(uint selfLayer)
    {
        using JsonDocument doc = JsonDocument.Parse(FileAccess.GetFileAsString(Dir + "cristal.json"), VillagerLooks.JsonOptions);
        JsonElement l = doc.RootElement.GetProperty("luz_da_v1_para_o_jogo");
        JsonElement c = l.GetProperty("cor");
        // Centro do cristal no espaço do corpo (glTF); o encaixe Peito está no espaço do corpo em repouso.
        JsonElement at = doc.RootElement.GetProperty("centro_gltf_m");
        return new OmniLight3D
        {
            Name = "CrystalLight",
            LightColor = new Color(c[0].GetSingle(), c[1].GetSingle(), c[2].GetSingle()),
            LightEnergy = l.GetProperty("energia").GetSingle(),
            OmniRange = l.GetProperty("alcance_m").GetSingle(),
            OmniAttenuation = l.GetProperty("atenuacao").GetSingle(),
            ShadowEnabled = l.GetProperty("sombra").GetBoolean(),
            LightSpecular = l.GetProperty("especular").GetSingle(),
            LightCullMask = ~selfLayer,
            Position = new Vector3(at[0].GetSingle(), at[1].GetSingle(), at[2].GetSingle()),
        };
    }

    private static ShaderMaterial Toon(Color color, float shadowFloor)
    {
        var material = new ShaderMaterial { Shader = GD.Load<Shader>(VillagerLooks.ToonShaderPath) };
        material.SetShaderParameter("albedo", color);
        material.SetShaderParameter("shadow_floor", shadowFloor);
        VisualSettings.Current.ApplyRim(material); // contrato: borda fria ligada só nela (o aldeão não)
        Outline.Attach(material);
        return material;
    }

    /// <summary>Encaixe preso ao osso, compensando a pose de repouso: uma peça no espaço do corpo entra sem ajuste.</summary>
    private static Node3D? Socket(Skeleton3D skeleton, Transform3D skeletonInModel, string boneName, string socketName)
    {
        int bone = skeleton.FindBone(boneName);
        if (bone < 0)
        {
            GD.PushWarning($"Protagonista v2: osso \"{boneName}\" não existe; sem o encaixe \"{socketName}\".");
            return null;
        }
        var attachment = new BoneAttachment3D { Name = socketName + "Attach", BoneName = boneName };
        skeleton.AddChild(attachment);
        var socket = new Node3D
        {
            Name = socketName,
            Transform = skeleton.GetBoneGlobalRest(bone).AffineInverse() * skeletonInModel.AffineInverse(),
        };
        attachment.AddChild(socket);
        return socket;
    }

    private static void Reparent(MeshInstance3D mesh, Node3D socket)
    {
        Node owner = mesh.Owner ?? mesh.GetParent();
        Transform3D global = Transform3D.Identity;
        for (Node n = mesh; n is Node3D n3 && n != owner; n = n.GetParent())
            global = n3.Transform * global;
        mesh.GetParent().RemoveChild(mesh);
        mesh.Owner = null;
        socket.AddChild(mesh);
        mesh.Transform = global; // posição da peça no espaço do corpo (o GLB dela tem a mesma origem)
        owner.QueueFree();
    }

    private static T? First<T>(Node root) where T : Node
    {
        foreach (T node in VillagerLooks.Descendants<T>(root))
            return node;
        return null;
    }

    private static float ReadStride()
    {
        using JsonDocument doc = JsonDocument.Parse(FileAccess.GetFileAsString(Dir + "clipes/clipes.json"), VillagerLooks.JsonOptions);
        return doc.RootElement.GetProperty(RunClipInJson).GetProperty("passada_m_s").GetSingle();
    }

    private sealed record Looks(Color Skin, Color Hair, Color Horn, Color Cloth, float ShadowFloor);

    private static Looks ReadLooks()
    {
        using JsonDocument doc = JsonDocument.Parse(FileAccess.GetFileAsString(GameFiles.Castellan), VillagerLooks.JsonOptions);
        JsonElement l = doc.RootElement.GetProperty("looks");
        Color C(string name) => new(l.GetProperty(name).GetString() ?? "#FF00FF");
        return new Looks(C("skin"), C("hair"), C("horn"), C("cloth"), l.GetProperty("shadowFloor").GetSingle());
    }
}
