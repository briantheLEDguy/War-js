#include "WarContentSubsystem.h"
#include "Dom/JsonObject.h"

namespace
{
    bool NameField(const TSharedPtr<FJsonObject>& Row, const TCHAR* Key, FName& Out, bool Optional = false)
    {
        if (Optional && !Row->HasField(Key)) { Out = NAME_None; return true; }
        FString Text;
        if (!Row->TryGetStringField(Key, Text) || Text.TrimStartAndEnd().IsEmpty()) return false;
        Out = FName(*Text); return !Out.IsNone();
    }
    bool IntegerField(const TSharedPtr<FJsonObject>& Row, const TCHAR* Key, int32& Out, int32 Min = 0)
    {
        double Number;
        if (!Row->TryGetNumberField(Key, Number) || !FMath::IsFinite(Number) || Number < Min
            || Number > MAX_int32 || FMath::FloorToDouble(Number) != Number) return false;
        Out = int32(Number); return true;
    }
    TSharedPtr<FJsonObject> Object(const TSharedPtr<FJsonValue>& Value)
    { return Value.IsValid() && Value->Type == EJson::Object ? Value->AsObject() : nullptr; }
}

bool UWarContentSubsystem::GetQuest(FName Id, FWarQuestDefinition& Quest, FString& Error) const
{
    Error.Reset();
    const auto* Found = bReady ? QuestCatalog.Find(Id) : nullptr;
    if (!Found) { Error = TEXT("Quest catalog is unavailable or quest is unknown."); return false; }
    Quest = *Found; return true;
}

TArray<FWarQuestDefinition> UWarContentSubsystem::GetQuestsForNpc(FName Zone, FName Npc) const
{
    TArray<FWarQuestDefinition> Result;
    if (!bReady) return Result;
    for (const auto& Pair : QuestCatalog)
    {
        const auto& Quest = Pair.Value;
        if ((Quest.GiverNpcId == Npc && (Quest.GiverZoneId.IsNone() || Quest.GiverZoneId == Zone))
            || (Quest.TurninNpcId == Npc && (Quest.TurninZoneId.IsNone() || Quest.TurninZoneId == Zone))) Result.Add(Quest);
    }
    Result.Sort([](const auto& A, const auto& B) { return A.Id.LexicalLess(B.Id); });
    return Result;
}

bool UWarContentSubsystem::GetQuestNpc(FName Zone, FName Npc, FString& Name, FName& Profile, FString& Error, bool* bMeasureHeight) const
{
    if (!bReady) { Error = TEXT("Quest catalog is unavailable."); return false; }
    return ParseQuestNpc(Manifest, Zone, Npc, Name, Profile, Error, bMeasureHeight);
}

bool UWarContentSubsystem::ParseQuestNpc(const TSharedPtr<FJsonObject>& Catalog, FName Zone, FName Npc,
    FString& Name, FName& Profile, FString& Error, bool* bMeasureHeight)
{
    Error = TEXT("Quest NPC identity is unknown or ambiguous.");
    const TArray<TSharedPtr<FJsonValue>>* Maps = nullptr;
    if (!Catalog || Zone.IsNone() || Npc.IsNone() || !Catalog->TryGetArrayField(TEXT("maps"), Maps)) return false;
    int32 Matches = 0, ZoneMatches = 0; FString ParsedName; FName ParsedProfile; bool Height = false;
    for (const auto& Value : *Maps)
    {
        const auto Map = Object(Value); FName MapId;
        if (!Map || !NameField(Map, TEXT("id"), MapId)) return false;
        if (MapId != Zone) continue;
        if (++ZoneMatches != 1) return false;
        const TSharedPtr<FJsonObject>* Definition = nullptr;
        const TArray<TSharedPtr<FJsonValue>>* Npcs = nullptr;
        if (!Map->TryGetObjectField(TEXT("definition"), Definition) || !(*Definition)->TryGetArrayField(TEXT("npcs"), Npcs)) return false;
        for (const auto& Entry : *Npcs)
        {
            const auto Row = Object(Entry); FName Id;
            if (!Row || !NameField(Row, TEXT("id"), Id)) return false;
            if (Id != Npc) continue;
            FString Role;
            if (++Matches != 1 || !Row->TryGetStringField(TEXT("role"), Role) || Role != TEXT("questgiver")
                || !Row->TryGetStringField(TEXT("name"), ParsedName) || ParsedName.IsEmpty()
                || !NameField(Row, TEXT("characterProfileKey"), ParsedProfile)) return false;
            const TSharedPtr<FJsonObject>* Crater = nullptr;
            double Y;
            Height = (*Definition)->TryGetObjectField(TEXT("craterCity"), Crater) && Row->TryGetNumberField(TEXT("y"), Y);
        }
    }
    if (Matches != 1) return false;
    Name = ParsedName; Profile = ParsedProfile; if (bMeasureHeight) *bMeasureHeight = Height; Error.Reset(); return true;
}

bool UWarContentSubsystem::ParseQuestCatalog(const TSharedPtr<FJsonObject>& Catalog,
    TMap<FName, FWarQuestDefinition>& Quests, FString& Error)
{
    Error = TEXT("Quest catalog contains invalid definitions or references.");
    const TArray<TSharedPtr<FJsonValue>> *Rows = nullptr, *Items = nullptr, *Maps = nullptr;
    const TSharedPtr<FJsonObject>* ItemGroup = nullptr;
    if (!Catalog.IsValid() || !Catalog->TryGetArrayField(TEXT("quests"), Rows) || Rows->IsEmpty()
        || !Catalog->TryGetObjectField(TEXT("items"), ItemGroup) || !(*ItemGroup)->TryGetArrayField(TEXT("definitions"), Items)
        || !Catalog->TryGetArrayField(TEXT("maps"), Maps)) return false;
    TMap<FName, TSharedPtr<FJsonObject>> ItemDefinitions;
    for (const auto& Value : *Items)
    {
        const auto Row = Object(Value); FName Id;
        if (!Row.IsValid() || !NameField(Row, TEXT("key"), Id) || ItemDefinitions.Contains(Id)) return false;
        ItemDefinitions.Add(Id, Row);
    }
    TSet<FName> Zones;
    for (const auto& Value : *Maps)
    {
        const auto Row = Object(Value); FName Id;
        if (!Row.IsValid() || !NameField(Row, TEXT("id"), Id) || Zones.Contains(Id)) return false;
        Zones.Add(Id);
    }
    TMap<FName, FWarQuestDefinition> Parsed;
    for (const auto& Value : *Rows)
    {
        const auto Row = Object(Value); FWarQuestDefinition Quest;
        if (!Row.IsValid() || !NameField(Row, TEXT("id"), Quest.Id) || Parsed.Contains(Quest.Id)
            || !NameField(Row, TEXT("realm"), Quest.Realm, true)
            || (!Quest.Realm.IsNone() && Quest.Realm != TEXT("aegis") && Quest.Realm != TEXT("riftbound"))
            || !NameField(Row, TEXT("giverNpcId"), Quest.GiverNpcId) || !NameField(Row, TEXT("turninNpcId"), Quest.TurninNpcId)
            || !NameField(Row, TEXT("giverZoneId"), Quest.GiverZoneId, true) || !NameField(Row, TEXT("turninZoneId"), Quest.TurninZoneId, true)
            || (!Quest.GiverZoneId.IsNone() && !Zones.Contains(Quest.GiverZoneId))
            || (!Quest.TurninZoneId.IsNone() && !Zones.Contains(Quest.TurninZoneId))
            || !NameField(Row, TEXT("prereqQuestId"), Quest.Prerequisite, true)
            || !IntegerField(Row, TEXT("minLevel"), Quest.MinLevel, 1)
            || !Row->TryGetStringField(TEXT("title"), Quest.Title) || Quest.Title.IsEmpty()
            || !Row->TryGetStringField(TEXT("description"), Quest.Description)) return false;
        const TArray<TSharedPtr<FJsonValue>>* Objectives = nullptr;
        const TSharedPtr<FJsonObject>* Reward = nullptr;
        if (!Row->TryGetArrayField(TEXT("objectives"), Objectives) || Objectives->IsEmpty()
            || !Row->TryGetObjectField(TEXT("reward"), Reward)
            || !IntegerField(*Reward, TEXT("xp"), Quest.Xp) || !IntegerField(*Reward, TEXT("gold"), Quest.Gold)) return false;
        TSet<FName> ObjectiveIds;
        for (const auto& Entry : *Objectives)
        {
            const auto Definition = Object(Entry); FWarQuestObjective Objective;
            if (!Definition.IsValid() || !NameField(Definition, TEXT("id"), Objective.Id) || ObjectiveIds.Contains(Objective.Id)
                || !NameField(Definition, TEXT("zoneId"), Objective.ZoneId, true)
                || (!Objective.ZoneId.IsNone() && !Zones.Contains(Objective.ZoneId))
                || !Definition->TryGetStringField(TEXT("killTarget"), Objective.KillTarget) || Objective.KillTarget.IsEmpty()
                || !Definition->TryGetStringField(TEXT("description"), Objective.Description) || Objective.Description.IsEmpty()
                || !IntegerField(Definition, TEXT("required"), Objective.Required, 1)) return false;
            ObjectiveIds.Add(Objective.Id); Quest.Objectives.Add(Objective);
        }
        const TArray<TSharedPtr<FJsonValue>>* Outputs = nullptr;
        if ((*Reward)->HasField(TEXT("items")))
        {
            if (!(*Reward)->TryGetArrayField(TEXT("items"), Outputs)) return false;
            for (const auto& Entry : *Outputs)
            {
                const auto Definition = Object(Entry); FWarQuestReward Output;
                if (!Definition.IsValid() || !NameField(Definition, TEXT("key"), Output.Item.Key)
                    || !IntegerField(Definition, TEXT("qty"), Output.Item.Quantity, 1)) return false;
                const auto* Item = ItemDefinitions.Find(Output.Item.Key);
                if (!Item || !NameField(*Item, TEXT("kind"), Output.Item.Kind)
                    || !NameField(*Item, TEXT("equipSlot"), Output.Item.EquipSlot, true)) return false;
                if (Definition->HasField(TEXT("kind")) && !NameField(Definition, TEXT("kind"), Output.Item.Kind)) return false;
                if (Definition->HasField(TEXT("equipSlot")) && !NameField(Definition, TEXT("equipSlot"), Output.Item.EquipSlot)) return false;
                const TSharedPtr<FJsonObject>* Roll = nullptr;
                if (Definition->HasField(TEXT("strengthRoll")))
                {
                    if (!Definition->TryGetObjectField(TEXT("strengthRoll"), Roll)
                        || !IntegerField(*Roll, TEXT("min"), Output.MinimumStrength)
                        || !IntegerField(*Roll, TEXT("max"), Output.MaximumStrength)
                        || Output.MaximumStrength < Output.MinimumStrength
                        || int64(Output.MaximumStrength) - Output.MinimumStrength + 1 > MAX_int32) return false;
                    Output.bRollStrength = true;
                }
                auto Probe = Output.Item; Probe.Quantity = 1; Probe.Slot = 0; FString ItemError;
                if (!WarInventory::Validate({Probe}, ItemError)) return false;
                Quest.Rewards.Add(Output);
            }
        }
        Parsed.Add(Quest.Id, MoveTemp(Quest));
    }
    // Resolve every chain, rejecting missing prerequisites, cycles and impossible cross-realm chains.
    for (const auto& Pair : Parsed)
    {
        TSet<FName> Seen; const FWarQuestDefinition* Current = &Pair.Value;
        while (Current)
        {
            if (Seen.Contains(Current->Id)) return false;
            Seen.Add(Current->Id);
            if (Current->Prerequisite.IsNone()) break;
            const auto* Previous = Parsed.Find(Current->Prerequisite);
            if (!Previous || (!Pair.Value.Realm.IsNone() && !Previous->Realm.IsNone() && Pair.Value.Realm != Previous->Realm)) return false;
            Current = Previous;
        }
    }
    Quests = MoveTemp(Parsed); Error.Reset(); return true;
}
