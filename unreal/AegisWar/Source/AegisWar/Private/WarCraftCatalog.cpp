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
