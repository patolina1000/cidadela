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

    private readonly Dictionary<string, BuildingType> _buildingByKind = new();
    private readonly Dictionary<string, ItemType> _itemByKind = new();
    private readonly Dictionary<string, RecipeType> _recipeByMachine = new();

    private GameData(List<ItemType> items, IReadOnlyDictionary<string, ResourceType> resources, CastellanStats castellan,
        VillagerStats villagers, List<BuildingType> buildings, List<RecipeType> recipes)
    {
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

    public ResourceType Resource(string kind) =>
        Resources.TryGetValue(kind, out ResourceType? type)
            ? type
            : throw new FormatException($"Recurso desconhecido: \"{kind}\".");

    public static GameData Parse(string itemsJson, string resourcesJson, string castellanJson,
        string villagersJson, string buildingsJson, string recipesJson)
    {
        var items = new List<ItemType>();
        foreach ((string kind, ItemData i) in Ordered<ItemData>(itemsJson, "items.json"))
            items.Add(new ItemType(kind, i.Name, i.Color));
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
            resources[kind] = new ResourceType(kind, item.Name, SecondsToTicks(r.GatherSeconds), r.Amount);
        }

        var c = JsonSerializer.Deserialize<CastellanData>(castellanJson, JsonOptions)
            ?? throw new FormatException("castellan.json vazio.");
        if (c.Speed <= 0f || c.RunSpeed < c.Speed)
            throw new FormatException("castellan.json: speed precisa ser positivo e runSpeed não pode ser menor que speed.");
        var stats = new CastellanStats(c.Speed, c.Reach, c.GatherReach, c.Radius, c.RunSpeed);

        var buildings = new List<BuildingType>();
        foreach ((string kind, BuildingData b) in Ordered<BuildingData>(buildingsJson, "buildings.json"))
        {
            CheckItems(itemKinds, b.Cost, $"custo de \"{kind}\"");
            if (b.BeltSpeed < 0f)
                throw new FormatException($"beltSpeed negativo em \"{kind}\".");
            JobType? job = null;
            if (b.Job is JobData j)
            {
                if (!resources.ContainsKey(j.Resource) || j.Radius <= 0f || j.Capacity <= 0)
                    throw new FormatException($"Ofício inválido em \"{kind}\": precisa de um recurso, radius e capacity positivos.");
                job = new JobType(j.Name, j.Resource, j.Radius, j.Capacity);
            }
            buildings.Add(new BuildingType(kind, b.Name, b.Cost, b.Solid, b.BeltSpeed, b.Storage, job));
        }

        var recipes = new List<RecipeType>();
        foreach ((string id, RecipeData r) in Ordered<RecipeData>(recipesJson, "recipes.json"))
        {
            if (!buildings.Exists(b => b.Kind == r.Machine))
                throw new FormatException($"Receita \"{id}\": máquina desconhecida \"{r.Machine}\".");
            if (recipes.Exists(x => x.Machine == r.Machine))
                throw new FormatException($"Receita \"{id}\": \"{r.Machine}\" já tem receita (por enquanto, uma por máquina).");
            if (r.Seconds <= 0f || r.Inputs.Count == 0 || r.Outputs.Count == 0)
                throw new FormatException($"Receita \"{id}\" precisa de entradas, saídas e seconds positivos.");
            CheckItems(itemKinds, r.Inputs, $"entradas de \"{id}\"");
            CheckItems(itemKinds, r.Outputs, $"saídas de \"{id}\"");
            recipes.Add(new RecipeType(id, r.Machine, r.Inputs, r.Outputs, SecondsToTicks(r.Seconds)));
        }

        var v = JsonSerializer.Deserialize<VillagerData>(villagersJson, JsonOptions)
            ?? throw new FormatException("villagers.json vazio.");
        if (v.Speed <= 0f || v.GatherMultiplier <= 0f || v.Carry <= 0)
            throw new FormatException("villagers.json: speed, gatherMultiplier e carry precisam ser positivos.");
        var villagers = new VillagerStats(v.Speed, v.GatherMultiplier, v.Carry);

        return new GameData(items, resources, stats, villagers, buildings, recipes);
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
    }

    private sealed class JobData
    {
        public string Name { get; set; } = "";
        public string Resource { get; set; } = "";
        public float Radius { get; set; }
        public int Capacity { get; set; }
    }

    private sealed class VillagerData
    {
        public float Speed { get; set; } = 3f;
        public float GatherMultiplier { get; set; } = 1.5f;
        public int Carry { get; set; } = 5;
    }

    private sealed class ResourceData
    {
        public float GatherSeconds { get; set; }
        public int Amount { get; set; }
    }

    private sealed class CastellanData
    {
        public float Speed { get; set; } = 6f;
        public float RunSpeed { get; set; } = 6f;
        public float Reach { get; set; } = 10f;
        public float GatherReach { get; set; } = 1f;
        public float Radius { get; set; } = 0.3f;
    }
}
