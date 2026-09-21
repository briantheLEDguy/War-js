#include "WarContentSubsystem.h"
#include "Dom/JsonObject.h"

namespace
{
    bool Integer(const TSharedPtr<FJsonObject>& Object, const TCHAR* Field, int32& Out, int32 Minimum = 0)
    {
        double Value;
        if (!Object->TryGetNumberField(Field, Value) || !FMath::IsFinite(Value)
            || Value < Minimum || Value > MAX_int32 || FMath::FloorToDouble(Value) != Value) return false;
        Out = static_cast<int32>(Value);
        return true;
    }

    TSharedPtr<FJsonObject> FindDefinition(const TSharedPtr<FJsonObject>& Root, const TCHAR* Section,
        const TCHAR* Array, const TCHAR* KeyField, const FName Key)
    {
        const TSharedPtr<FJsonObject>* Group = nullptr;
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (!Root.IsValid() || !Root->TryGetObjectField(Section, Group) || !(*Group)->TryGetArrayField(Array, Values)) return nullptr;
        TSharedPtr<FJsonObject> Found;
        for (const auto& Value : *Values)
        {
            if (!Value.IsValid() || Value->Type != EJson::Object) return nullptr;
            const auto Object = Value->AsObject();
            FString Name;
            if (!Object->TryGetStringField(KeyField, Name)) return nullptr;
            if (FName(*Name) != Key) continue;
            if (Found.IsValid()) return nullptr;
            Found = Object;
        }
        return Found;
    }
}

bool UWarContentSubsystem::GetCraftRecipe(const FName Id, FWarCraftRecipe& Recipe, FString& Error) const
{
    if (!bReady) { Error = TEXT("Crafting catalog is unavailable."); return false; }
    return ParseCraftRecipe(Manifest, Id, Recipe, Error);
}

bool UWarContentSubsystem::ResolveInventoryItem(const FName Key, const int32 Quantity, FWarInventoryItem& Item) const
{
    if (!bReady || Quantity <= 0) return false;
    const auto Definition = FindDefinition(Manifest, TEXT("items"), TEXT("definitions"), TEXT("key"), Key);
    FString Kind, Slot;
    if (!Definition.IsValid() || !Definition->TryGetStringField(TEXT("kind"), Kind)) return false;
    Definition->TryGetStringField(TEXT("equipSlot"), Slot);
    FWarInventoryItem Resolved;
    Resolved.Key = Key; Resolved.Quantity = Quantity; Resolved.Kind = FName(*Kind); Resolved.EquipSlot = FName(*Slot);
    Item = Resolved;
    return true;
}

TArray<FName> UWarContentSubsystem::GetCraftRecipeIds() const
{
    TArray<FName> Result;
    const TSharedPtr<FJsonObject>* Group = nullptr;
    const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
    if (!bReady || !Manifest.IsValid() || !Manifest->TryGetObjectField(TEXT("crafting"), Group)
        || !(*Group)->TryGetArrayField(TEXT("recipes"), Values)) return Result;
    for (const auto& Value : *Values)
    {
        FString Id;
        if (!Value.IsValid() || Value->Type != EJson::Object || !Value->AsObject()->TryGetStringField(TEXT("id"), Id)) return {};
        FWarCraftRecipe Recipe; FString Error;
        if (!GetCraftRecipe(FName(*Id), Recipe, Error)) return {};
        Result.Add(Recipe.Id);
    }
    return Result;
}

bool UWarContentSubsystem::ParseCraftRecipe(const TSharedPtr<FJsonObject>& Catalog, const FName Id,
    FWarCraftRecipe& Recipe, FString& Error)
{
    Error = TEXT("Unknown or invalid crafting recipe.");
    const auto Definition = FindDefinition(Catalog, TEXT("crafting"), TEXT("recipes"), TEXT("id"), Id);
    if (!Definition.IsValid()) return false;
    FWarCraftRecipe Parsed;
    Parsed.Id = Id;
    FString Profession, Station;
    if (!Definition->TryGetStringField(TEXT("professionId"), Profession) || Profession.IsEmpty()
        || !Definition->TryGetStringField(TEXT("station"), Station) || Station.IsEmpty()
        || !Definition->TryGetStringField(TEXT("name"), Parsed.Name)
        || !Integer(Definition, TEXT("minRank"), Parsed.MinimumRank, 1) || !Integer(Definition, TEXT("xp"), Parsed.Xp)) return false;
    Parsed.Profession = FName(*Profession); Parsed.Station = FName(*Station);
    if (!FindDefinition(Catalog, TEXT("crafting"), TEXT("professions"), TEXT("id"), Parsed.Profession).IsValid()) return false;
    const TArray<TSharedPtr<FJsonValue>>* Inputs = nullptr;
    const TArray<TSharedPtr<FJsonValue>>* Outputs = nullptr;
    if (!Definition->TryGetArrayField(TEXT("inputs"), Inputs) || Inputs->IsEmpty()
        || !Definition->TryGetArrayField(TEXT("outputs"), Outputs) || Outputs->IsEmpty()) return false;
    for (const auto& Value : *Inputs)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) return false;
        FString Key; int32 Quantity;
        const auto Object = Value->AsObject();
        if (!Object->TryGetStringField(TEXT("key"), Key) || Key.IsEmpty() || !Integer(Object, TEXT("qty"), Quantity, 1)
            || Parsed.Inputs.Contains(FName(*Key))
            || !FindDefinition(Catalog, TEXT("items"), TEXT("definitions"), TEXT("key"), FName(*Key)).IsValid()) return false;
        Parsed.Inputs.Add(FName(*Key), Quantity);
    }
    for (const auto& Value : *Outputs)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) return false;
        const auto Object = Value->AsObject();
        FString Key, Kind, EquipSlot;
        FWarCraftReward Reward;
        if (!Object->TryGetStringField(TEXT("key"), Key) || Key.IsEmpty() || !Integer(Object, TEXT("qty"), Reward.Item.Quantity, 1)) return false;
        const auto Item = FindDefinition(Catalog, TEXT("items"), TEXT("definitions"), TEXT("key"), FName(*Key));
        if (!Item.IsValid() || !Item->TryGetStringField(TEXT("kind"), Kind)) return false;
        Item->TryGetStringField(TEXT("equipSlot"), EquipSlot);
        Object->TryGetStringField(TEXT("kind"), Kind);
        Object->TryGetStringField(TEXT("equipSlot"), EquipSlot);
        Reward.Item.Key = FName(*Key); Reward.Item.Kind = FName(*Kind); Reward.Item.EquipSlot = FName(*EquipSlot);
        const TSharedPtr<FJsonObject>* Roll = nullptr;
        if (Object->HasField(TEXT("strengthRoll")))
        {
            if (!Object->TryGetObjectField(TEXT("strengthRoll"), Roll)
                || !Integer(*Roll, TEXT("min"), Reward.MinimumStrength)
                || !Integer(*Roll, TEXT("max"), Reward.MaximumStrength)
                || Reward.MaximumStrength < Reward.MinimumStrength
                || static_cast<int64>(Reward.MaximumStrength) - Reward.MinimumStrength + 1 > MAX_int32) return false;
            Reward.bRollStrength = true;
        }
        Parsed.Outputs.Add(Reward);
    }
    Recipe = MoveTemp(Parsed);
    Error.Reset();
    return true;
}


bool UWarContentSubsystem::GetCultivationSeed(const FName Key, FWarCultivationSeed& Seed, FString& Error) const
{
    if (!bReady) { Error = TEXT("Cultivation catalog is unavailable."); return false; }
    return ParseCultivationSeed(Manifest, Key, Seed, Error);
}

bool UWarContentSubsystem::ParseCultivationSeed(const TSharedPtr<FJsonObject>& Catalog, const FName Key,
    FWarCultivationSeed& Seed, FString& Error)
{
    Error = TEXT("Unknown or invalid cultivation seed.");
    const auto Definition = FindDefinition(Catalog, TEXT("crafting"), TEXT("seeds"), TEXT("seedKey"), Key);
    const TSharedPtr<FJsonObject>* Group = nullptr;
    if (!Definition.IsValid() || !Catalog->TryGetObjectField(TEXT("crafting"), Group)
        || !FindDefinition(Catalog, TEXT("items"), TEXT("definitions"), TEXT("key"), Key).IsValid()) return false;
    FWarCultivationSeed Parsed; Parsed.Key = Key;
    if (!Definition->TryGetStringField(TEXT("name"), Parsed.Name)
        || !Integer(Definition, TEXT("durationMs"), Parsed.DurationMs, 1)
        || !Integer(Definition, TEXT("xp"), Parsed.Xp)
        || !Integer(*Group, TEXT("cultivationSlotCount"), Parsed.SlotLimit, 1)) return false;
    FString Additive;
    if (Definition->HasField(TEXT("bonusAdditiveKey")))
    {
        if (!Definition->TryGetStringField(TEXT("bonusAdditiveKey"), Additive) || Additive.IsEmpty()
            || !FindDefinition(Catalog, TEXT("items"), TEXT("definitions"), TEXT("key"), FName(*Additive)).IsValid()) return false;
        Parsed.Additive = FName(*Additive);
    }
    const auto ReadOutputs = [&](const TCHAR* Field, TArray<FWarInventoryItem>& Out) {
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (!Definition->TryGetArrayField(Field, Values) || Values->IsEmpty()) return false;
        for (const auto& Value : *Values)
        {
            if (!Value.IsValid() || Value->Type != EJson::Object) return false;
            const auto Object = Value->AsObject();
            FString ItemKey, Kind, Slot; FWarInventoryItem Item;
            if (!Object->TryGetStringField(TEXT("key"), ItemKey) || ItemKey.IsEmpty()
                || !Integer(Object, TEXT("qty"), Item.Quantity, 1)) return false;
            const auto Entry = FindDefinition(Catalog, TEXT("items"), TEXT("definitions"), TEXT("key"), FName(*ItemKey));
            if (!Entry.IsValid() || !Entry->TryGetStringField(TEXT("kind"), Kind)) return false;
            Entry->TryGetStringField(TEXT("equipSlot"), Slot);
            Item.Key = FName(*ItemKey); Item.Kind = FName(*Kind); Item.EquipSlot = FName(*Slot);
            Out.Add(Item);
        }
        return true;
    };
    if (!ReadOutputs(TEXT("outputs"), Parsed.Outputs)) return false;
    if (Definition->HasField(TEXT("bonusOutputs"))
        && (Parsed.Additive.IsNone() || !ReadOutputs(TEXT("bonusOutputs"), Parsed.BonusOutputs))) return false;
    Seed = MoveTemp(Parsed); Error.Reset(); return true;
}


bool UWarContentSubsystem::GetResourceNode(const FName ZoneId, const FName NodeId,
    FWarResourceDefinition& Node, FString& Error) const
{
    if (!bReady) { Error = TEXT("Resource catalog is unavailable."); return false; }
    return ParseResourceNode(Manifest, ZoneId, NodeId, Node, Error);
}

bool UWarContentSubsystem::ParseResourceNode(const TSharedPtr<FJsonObject>& Catalog, const FName ZoneId,
    const FName NodeId, FWarResourceDefinition& Node, FString& Error)
{
    Error = TEXT("Unknown or invalid resource node.");
    const TArray<TSharedPtr<FJsonValue>>* Maps = nullptr;
    if (!Catalog.IsValid() || ZoneId.IsNone() || NodeId.IsNone() || !Catalog->TryGetArrayField(TEXT("maps"), Maps)) return false;
    TSharedPtr<FJsonObject> Map;
    for (const auto& Value : *Maps)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) return false;
        FString Id;
        if (!Value->AsObject()->TryGetStringField(TEXT("id"), Id)) return false;
        if (FName(*Id) != ZoneId) continue;
        if (Map.IsValid()) return false;
        const TSharedPtr<FJsonObject>* Definition = nullptr;
        if (!Value->AsObject()->TryGetObjectField(TEXT("definition"), Definition)) return false;
        Map = *Definition;
    }
    const TArray<TSharedPtr<FJsonValue>>* Nodes = nullptr;
    if (!Map.IsValid() || !Map->TryGetArrayField(TEXT("resourceNodes"), Nodes)) return false;
    TSharedPtr<FJsonObject> Definition;
    for (const auto& Value : *Nodes)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) return false;
        FString Id;
        if (!Value->AsObject()->TryGetStringField(TEXT("id"), Id)) return false;
        if (FName(*Id) != NodeId) continue;
        if (Definition.IsValid()) return false;
        Definition = Value->AsObject();
    }
    if (!Definition.IsValid()) return false;
    FWarResourceDefinition Parsed; Parsed.ZoneId = ZoneId; Parsed.NodeId = NodeId;
    FString Profession, Visual;
    double Seconds = 0, Radius = 4.5;
    if (!Definition->TryGetStringField(TEXT("label"), Parsed.Label)
        || !Definition->TryGetStringField(TEXT("professionId"), Profession) || Profession.IsEmpty()
        || !FindDefinition(Catalog, TEXT("crafting"), TEXT("professions"), TEXT("id"), FName(*Profession)).IsValid()
        || !Definition->TryGetStringField(TEXT("visualPropId"), Visual) || Visual.IsEmpty()
        || !Integer(Definition, TEXT("xp"), Parsed.Xp)
        || !Definition->TryGetNumberField(TEXT("respawnSeconds"), Seconds) || !FMath::IsFinite(Seconds)
        || Seconds > MAX_int32 / 1000) return false;
    if (Definition->HasField(TEXT("radius")) && !Definition->TryGetNumberField(TEXT("radius"), Radius)) return false;
    if (!FMath::IsFinite(Radius) || Radius <= 0 || Radius > MAX_int32 / 100) return false;
    Parsed.Profession = FName(*Profession); Parsed.VisualPropId = FName(*Visual);
    Parsed.bMeasureHeight = Map->HasTypedField<EJson::Object>(TEXT("craterCity")) && Definition->HasField(TEXT("y"));
    Parsed.RadiusCm = static_cast<float>(Radius * 100);
    Parsed.CooldownMs = FMath::CeilToInt64(FMath::Max(1.0, Seconds) * 1000);
    const TArray<TSharedPtr<FJsonValue>>* Loot = nullptr;
    if (!Definition->TryGetArrayField(TEXT("loot"), Loot) || Loot->IsEmpty()) return false;
    for (const auto& Value : *Loot)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) return false;
        const auto Entry = Value->AsObject(); FWarGatheringLoot Reward;
        FString Key, Kind, Slot;
        if (!Entry->TryGetStringField(TEXT("key"), Key) || Key.IsEmpty()
            || !Integer(Entry, TEXT("qty"), Reward.Item.Quantity, 1)
            || !Entry->TryGetNumberField(TEXT("chance"), Reward.Chance)
            || !FMath::IsFinite(Reward.Chance) || Reward.Chance < 0 || Reward.Chance > 1) return false;
        Reward.MinimumQuantity = Reward.MaximumQuantity = Reward.Item.Quantity;
        if (Entry->HasField(TEXT("minQty")) && !Integer(Entry, TEXT("minQty"), Reward.MinimumQuantity, 1)) return false;
        if (Entry->HasField(TEXT("maxQty")) && !Integer(Entry, TEXT("maxQty"), Reward.MaximumQuantity, 1)) return false;
        if (Reward.MaximumQuantity < Reward.MinimumQuantity) return false;
        const auto Item = FindDefinition(Catalog, TEXT("items"), TEXT("definitions"), TEXT("key"), FName(*Key));
        if (!Item.IsValid() || !Item->TryGetStringField(TEXT("kind"), Kind)) return false;
        Item->TryGetStringField(TEXT("equipSlot"), Slot);
        Reward.Item.Key = FName(*Key); Reward.Item.Kind = FName(*Kind); Reward.Item.EquipSlot = FName(*Slot);
        Parsed.Loot.Add(Reward);
    }
    Node = MoveTemp(Parsed); Error.Reset(); return true;
}
