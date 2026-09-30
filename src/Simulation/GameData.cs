using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Cidadela.Simulation;

/// <summary>
/// Dados de balanceamento lidos dos JSON de data/. Recebe o texto, não o caminho,
/// para não depender do sistema de arquivos do Godot (res://).
/// </summary>
public sealed class GameData
{
    internal static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
    };

    /// <summary>Itens na ordem do arquivo (a ordem dos botões do inventário).</summary>
    public IReadOnlyList<ItemType> Items { get; }

    public IReadOnlyDictionary<string, ResourceType> Resources { get; }
    public CastellanStats Castellan { get; }
    public VillagerStats Villagers { get; }

    /// <summary>Construções na ordem do arquivo (a ordem da barra de construção).</summary>
    public IReadOnlyList<BuildingType> Buildings { get; }

    /// <summary>Terrenos do chão natural na ordem do arquivo (o índice guardado em cada célula).</summary>
    public IReadOnlyList<TerrainType> Terrains { get; }

    private readonly Dictionary<string, BuildingType> _buildingByKind = new();
    private readonly Dictionary<string, ItemType> _itemByKind = new();
    private readonly Dictionary<string, RecipeType> _recipeByMachine = new();

    private GameData(List<ItemType> items, IReadOnlyDictionary<string, ResourceType> resources, CastellanStats castellan,
        VillagerStats villagers, List<BuildingType> buildings, List<RecipeType> recipes, List<TerrainType> terrains)
    {
        Terrains = terrains;
        Villagers = villagers;
        Items = items;
        Resources = resources;
        Castellan = castellan;
        Buildings = buildings;
        foreach (ItemType item in items)
            _itemByKind[item.Kind] = item;
        foreach (BuildingType b in buildings)
            _buildingByKind[b.Kind] = b;
        foreach (RecipeType r in recipes)
            _recipeByMachine[r.Machine] = r;
    }

    public ItemType Item(string kind) =>
        _itemByKind.TryGetValue(kind, out ItemType? type)
            ? type
            : throw new FormatException($"Item desconhecido: \"{kind}\".");

    /// <summary>Receita que essa construção faz, ou null se não é máquina.</summary>
    public RecipeType? RecipeFor(string buildingKind) => _recipeByMachine.GetValueOrDefault(buildingKind);

    public BuildingType Building(string kind) =>
        _buildingByKind.TryGetValue(kind, out BuildingType? type)
            ? type
            : throw new FormatException($"Construção desconhecida: \"{kind}\".");

    public TerrainType Terrain(string kind) =>
        ((List<TerrainType>)Terrains).Find(t => t.Kind == kind)
            ?? throw new FormatException($"Terreno desconhecido: \"{kind}\".");

    public ResourceType Resource(string kind) =>
        Resources.TryGetValue(kind, out ResourceType? type)
            ? type
            : throw new FormatException($"Recurso desconhecido: \"{kind}\".");

    /// <summary>Sem <paramref name="terrainJson"/>, o chão é um terreno só ("grass", sem textura).</summary>
    public static GameData Parse(string itemsJson, string resourcesJson, string castellanJson,
        string villagersJson, string buildingsJson, string recipesJson, string? terrainJson = null)
    {
        var items = new List<ItemType>();
        foreach ((string kind, ItemData i) in Ordered<ItemData>(itemsJson, "items.json"))
            items.Add(new ItemType(kind, i.Name, i.Color, i.Raw));
        var itemKinds = new HashSet<string>();
        foreach (ItemType i in items)
            itemKinds.Add(i.Kind);

        var raw = JsonSerializer.Deserialize<Dictionary<string, ResourceData>>(resourcesJson, JsonOptions)
            ?? throw new FormatException("resources.json vazio.");
        var resources = new Dictionary<string, ResourceType>();
        foreach ((string kind, ResourceData r) in raw)
        {
            if (!itemKinds.Contains(kind))
                throw new FormatException($"Recurso \"{kind}\" não existe em items.json.");
            if (r.GatherSeconds <= 0f || r.Amount <= 0)
                throw new FormatException($"Recurso \"{kind}\" precisa de gatherSeconds e amount positivos.");
            ItemType item = items.Find(i => i.Kind == kind)!;
            var variants = new List<ResourceVariant>();
            if (r.Variants is { Count: > 0 })
                foreach (VariantData vd in r.Variants)
                    variants.Add(new ResourceVariant(vd.Weight, ShapeOf(kind, vd)));
            else if (r.TrunkRadius is float t)
                variants.Add(new ResourceVariant(1f, Circle(kind, t)));
            float minScale = r.Scale is { Count: 2 } ? r.Scale[0] : 1f, maxScale = r.Scale is { Count: 2 } ? r.Scale[1] : 1f;
            if (minScale <= 0f || maxScale < minScale)
                throw new FormatException($"Recurso \"{kind}\": scale precisa ser [mínima, máxima], positivas.");
            foreach (ResourceVariant rv in variants)
            {
                if (rv.Weight <= 0f)
                    throw new FormatException($"Recurso \"{kind}\": peso de variação precisa ser positivo.");
                foreach ((System.Numerics.Vector2 cc, float cr) in rv.Shape.Circles)
                    if ((cc.Length() + cr) * maxScale >= 0.5f)
                        throw new FormatException($"Recurso \"{kind}\": o círculo de bloqueio precisa ficar dentro da célula (0,5), já com a escala.");
                foreach (System.Numerics.Vector2 p in rv.Shape.Polygon)
                    if (p.Length() * maxScale > 0.6f)
                        throw new FormatException($"Recurso \"{kind}\": o polígono de bloqueio passa de 0,6 m do centro, já com a escala.");
            }
            resources[kind] = new ResourceType(kind, item.Name, SecondsToTicks(r.GatherSeconds), r.Amount, variants, minScale, maxScale);
        }

        var c = JsonSerializer.Deserialize<CastellanData>(castellanJson, JsonOptions)
            ?? throw new FormatException("castellan.json vazio.");
        if (c.Speed <= 0f)
            throw new FormatException("castellan.json: speed precisa ser positivo.");
        var stats = new CastellanStats(c.Speed, c.Reach, c.GatherReach, c.Radius, c.GatherSurfaceReach);

        var buildings = new List<BuildingType>();
        foreach ((string kind, BuildingData b) in Ordered<BuildingData>(buildingsJson, "buildings.json"))
        {
            CheckItems(itemKinds, b.Cost, $"custo de \"{kind}\"");
            if (b.BeltSpeed < 0f)
                throw new FormatException($"beltSpeed negativo em \"{kind}\".");
            if (b.SpeedBonus <= 0f)
                throw new FormatException($"speedBonus de \"{kind}\" precisa ser positivo.");
            JobType? job = null;
            if (b.Job is JobData j)
            {
                if (!resources.ContainsKey(j.Resource) || j.Radius <= 0f || j.Capacity <= 0)
                    throw new FormatException($"Ofício inválido em \"{kind}\": precisa de um recurso, radius e capacity positivos.");
                job = new JobType(j.Name, j.Resource, j.Radius, j.Capacity);
            }
            PostType? posts = null;
            if (b.Posts is PostData p)
            {
                if (p.Count <= 0 || string.IsNullOrWhiteSpace(p.Name) || string.IsNullOrWhiteSpace(p.Tool))
                    throw new FormatException($"Postos inválidos em \"{kind}\": precisa de count positivo, name e tool.");
                if (job is not null)
                    throw new FormatException($"\"{kind}\": cabana (job) não tem postos.");
                posts = new PostType(p.Count, p.Name, p.Tool);
            }
            CarrierType? carriers = null;
            if (b.Carriers is CarrierData cd)
            {
                if (cd.Count <= 0 || cd.Radius <= 0f || job is not null || posts is not null)
                    throw new FormatException($"Carregadores inválidos em \"{kind}\": count e radius positivos, sem job nem posts.");
                carriers = new CarrierType(cd.Count, cd.Radius);
            }
            TorqueType? torque = null;
            if (b.Torque is TorqueData td)
            {
                if (td.Supply < 0f || td.Demand < 0f || td.SpeedBonus <= 0f)
                    throw new FormatException($"Torque inválido em \"{kind}\": supply e demand não negativos, speedBonus positivo.");
                torque = new TorqueType(td.Supply, td.Demand, td.SpeedBonus);
            }
            if (b.CrankCells < 0 || (b.CrankCells > 0 && posts is null))
                throw new FormatException($"Manivela inválida em \"{kind}\": crankCells positivo e um posto.");
            buildings.Add(new BuildingType(kind, b.Name, b.Cost, b.Solid, b.BeltSpeed, b.Storage, job, b.SpeedBonus, posts, carriers,
                torque, b.NeedsWater, b.Powered, b.CrankCells));
        }

        var recipes = new List<RecipeType>();
        foreach ((string id, RecipeData r) in Ordered<RecipeData>(recipesJson, "recipes.json"))
        {
            if (!buildings.Exists(b => b.Kind == r.Machine))
                throw new FormatException($"Receita \"{id}\": máquina desconhecida \"{r.Machine}\".");
            if (recipes.Exists(x => x.Machine == r.Machine))
                throw new FormatException($"Receita \"{id}\": \"{r.Machine}\" já tem receita (por enquanto, uma por máquina).");
            if (r.Seconds <= 0f || r.Outputs.Count == 0)
                throw new FormatException($"Receita \"{id}\" precisa de saídas e seconds positivos (entradas podem faltar).");
            CheckItems(itemKinds, r.Inputs, $"entradas de \"{id}\"");
            CheckItems(itemKinds, r.Outputs, $"saídas de \"{id}\"");
            recipes.Add(new RecipeType(id, r.Machine, r.Inputs, r.Outputs, SecondsToTicks(r.Seconds)));
        }

        var v = JsonSerializer.Deserialize<VillagerData>(villagersJson, JsonOptions)
            ?? throw new FormatException("villagers.json vazio.");
        if (v.SpeedTiers.Count == 0)
            throw new FormatException("villagers.json: speedTiers precisa de ao menos um patamar (o base).");
        for (int i = 0; i < v.SpeedTiers.Count; i++)
            if (v.SpeedTiers[i] <= 0f || (i > 0 && v.SpeedTiers[i] < v.SpeedTiers[i - 1]))
                throw new FormatException("villagers.json: speedTiers precisam ser positivos e em ordem crescente.");
        if (v.PenaltySpeed <= 0f || v.PenaltySpeed > v.SpeedTiers[0])
            throw new FormatException("villagers.json: penaltySpeed precisa ser positivo e no máximo o patamar base.");
        if (v.MaxSpeed <= 0f || v.GatherMultiplier <= 0f || v.Carry <= 0)
            throw new FormatException("villagers.json: maxSpeed, gatherMultiplier e carry precisam ser positivos.");
        var villagers = new VillagerStats(v.SpeedTiers, v.PenaltySpeed / v.SpeedTiers[0], v.MaxSpeed, v.GatherMultiplier, v.Carry,
            v.Radius, v.ResourceCellCost);

        var terrains = new List<TerrainType>();
        if (terrainJson is null)
            terrains.Add(new TerrainType("grass", "Grama", "", 0, 1f));
        else
            foreach ((string kind, TerrainData t) in Ordered<TerrainData>(terrainJson, "terrain.json"))
            {
                if (t.GrassDensity is < 0f or > 1f)
                    throw new FormatException($"terrain.json: grassDensity de \"{kind}\" precisa estar entre 0 e 1.");
                terrains.Add(new TerrainType(kind, t.Name, t.Texture, terrains.Count, t.GrassDensity, t.Water, t.Color));
            }
        if (terrains.Count is 0 or > byte.MaxValue + 1)
            throw new FormatException("terrain.json precisa de 1 a 256 terrenos.");

        return new GameData(items, resources, stats, villagers, buildings, recipes, terrains);
    }

    private static int SecondsToTicks(float seconds) =>
        Math.Max(1, (int)MathF.Round(seconds * SimClock.TicksPerSecond));

    private static void CheckItems(HashSet<string> itemKinds, Dictionary<string, int> items, string where)
    {
        foreach ((string item, int amount) in items)
            if (!itemKinds.Contains(item) || amount <= 0)
                throw new FormatException($"Item inválido em {where}: {item} × {amount}.");
    }

    /// <summary>Lê um objeto JSON como lista de pares, mantendo a ordem do arquivo.</summary>
    private static List<(string Key, T Value)> Ordered<T>(string json, string file)
    {
        using JsonDocument doc = JsonDocument.Parse(json, new JsonDocumentOptions
        {
            CommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
        });
        var list = new List<(string, T)>();
        foreach (JsonProperty prop in doc.RootElement.EnumerateObject())
        {
            T value = prop.Value.Deserialize<T>(JsonOptions)
                ?? throw new FormatException($"{file}: \"{prop.Name}\" vazio.");
            list.Add((prop.Name, value));
        }
        return list;
    }

    private sealed class ItemData
    {
        public string Name { get; set; } = "";
        public string Color { get; set; } = "FF00FF";
        public bool Raw { get; set; }
    }

    private sealed class RecipeData
    {
        public string Machine { get; set; } = "";
        public Dictionary<string, int> Inputs { get; set; } = new();
        public Dictionary<string, int> Outputs { get; set; } = new();
        public float Seconds { get; set; }
    }

    private sealed class BuildingData
    {
        public string Name { get; set; } = "";
        public Dictionary<string, int> Cost { get; set; } = new();
        public bool Solid { get; set; } = true;
        public float BeltSpeed { get; set; }
        public bool Storage { get; set; }
        public JobData? Job { get; set; }
        public float SpeedBonus { get; set; } = 1f;
        public PostData? Posts { get; set; }
        public CarrierData? Carriers { get; set; }
        public TorqueData? Torque { get; set; }
        public bool NeedsWater { get; set; }
        public bool Powered { get; set; }
        public int CrankCells { get; set; }
    }

    private sealed class TorqueData
    {
        public float Supply { get; set; }
        public float Demand { get; set; }
        public float SpeedBonus { get; set; } = 1f;
    }

    private sealed class CarrierData
    {
        public int Count { get; set; }
        public float Radius { get; set; }
    }

    private sealed class PostData
    {
        public int Count { get; set; }
        public string Name { get; set; } = "";
        public string Tool { get; set; } = "";
    }

    private sealed class JobData
    {
        public string Name { get; set; } = "";
        public string Resource { get; set; } = "";
        public float Radius { get; set; }
        public int Capacity { get; set; }
    }

    private sealed class TerrainData
    {
        public string Name { get; set; } = "";
        public string Texture { get; set; } = "";
        public float GrassDensity { get; set; }
        public bool Water { get; set; }
        public string Color { get; set; } = "";
    }

    private sealed class VillagerData
    {
        public List<float> SpeedTiers { get; set; } = new();
        public float PenaltySpeed { get; set; }
        public float MaxSpeed { get; set; } = 1.5f;
        public float GatherMultiplier { get; set; } = 1.5f;
        public int Carry { get; set; } = 5;
        public float Radius { get; set; } = 0.15f;
        public float ResourceCellCost { get; set; } = 0.5f;
    }

    private sealed class ResourceData
    {
        public float GatherSeconds { get; set; }
        public int Amount { get; set; }
        public float? TrunkRadius { get; set; }
        public List<VariantData>? Variants { get; set; }
        public List<float>? Scale { get; set; }
    }

    private static ResourceShape Circle(string kind, float radius)
    {
        if (radius <= 0f)
            throw new FormatException($"Recurso \"{kind}\": o raio de bloqueio precisa ser positivo.");
        return new ResourceShape(new[] { (System.Numerics.Vector2.Zero, radius) }, Array.Empty<System.Numerics.Vector2>());
    }

    private static ResourceShape ShapeOf(string kind, VariantData v)
    {
        if (v.Polygon is { Count: >= 3 })
        {
            var points = new List<System.Numerics.Vector2>();
            foreach (List<float> p in v.Polygon)
                points.Add(new System.Numerics.Vector2(p[0], p[1]));
            List<System.Numerics.Vector2> convex;
            try { convex = ResourceShape.ConvexPolygon(points); }
            catch (FormatException e) { throw new FormatException($"Recurso \"{kind}\": {e.Message}"); }
            return new ResourceShape(Array.Empty<(System.Numerics.Vector2, float)>(), convex);
        }
        return Circle(kind, v.Radius ?? 0f);
    }

    private sealed class VariantData
    {
        public float Weight { get; set; } = 1f;
        public float? Radius { get; set; }
        public List<List<float>>? Polygon { get; set; }
    }

    private sealed class CastellanData
    {
        public float Speed { get; set; } = 6f;
        public float Reach { get; set; } = 10f;
        public float GatherReach { get; set; } = 1f;
        public float Radius { get; set; } = 0.3f;
        public float GatherSurfaceReach { get; set; } = 1.3f;
    }
}
