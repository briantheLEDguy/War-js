#include "WarEnemyRules.h"
#include "Dom/JsonObject.h"

namespace
{
    bool Number(const TSharedPtr<FJsonObject>& Row, const TCHAR* Key, double& Out, double Maximum)
    {
        return Row->TryGetNumberField(Key, Out) && FMath::IsFinite(Out) && Out > 0 && Out <= Maximum;
    }
}

bool WarEnemies::Parse(const TSharedPtr<const FJsonObject>& Catalog, FName Zone, FName Id,
    FWarEnemyDefinition& Out, FString& Error)
{
    Error = TEXT("Enemy source identity, statistics or supported behavior is unavailable.");
    const TArray<TSharedPtr<FJsonValue>>* Maps = nullptr;
    if (!Catalog || Zone.IsNone() || Id.IsNone() || !Catalog->TryGetArrayField(TEXT("maps"), Maps)) return false;
    int32 Zones = 0, Matches = 0;
    FWarEnemyDefinition Result; Result.Zone = Zone; Result.Id = Id;
    for (const auto& Value : *Maps)
    {
        if (!Value || Value->Type != EJson::Object) return false;
        const auto Map = Value->AsObject(); FString MapId;
        if (!Map->TryGetStringField(TEXT("id"), MapId)) return false;
        if (FName(*MapId) != Zone) continue;
        const TSharedPtr<FJsonObject>* Definition = nullptr;
        const TArray<TSharedPtr<FJsonValue>>* Enemies = nullptr;
        if (++Zones != 1 || !Map->TryGetObjectField(TEXT("definition"), Definition)
            || !(*Definition)->TryGetArrayField(TEXT("enemies"), Enemies)) return false;
        for (const auto& Entry : *Enemies)
        {
            if (!Entry || Entry->Type != EJson::Object) return false;
            const auto Row = Entry->AsObject(); FString RowId, Archetype, Profile;
            if (!Row->TryGetStringField(TEXT("id"), RowId)) return false;
            if (FName(*RowId) != Id) continue;
            FString AssetKey;
            Row->TryGetStringField(TEXT("assetKey"), AssetKey);
            const bool bDummy = (Zone == TEXT("aegis_capital") && AssetKey == TEXT("dummy"))
                || (Zone == TEXT("riftspire_capital") && AssetKey == TEXT("riftspire_training_dummy"));
            if (bDummy)
            {
                double Level, Health, Aggro;
                const FString Model = AssetKey == TEXT("dummy") ? TEXT("prop_training_dummy_t1.glb") : TEXT("prop_riftspire_training_dummy.glb");
                FString AuthoredModel;
                if (++Matches != 1 || Row->HasField(TEXT("encounter")) || Row->HasField(TEXT("characterProfileKey"))
                    || Row->HasField(TEXT("archetype"))
                    || !RowId.StartsWith(Zone.ToString() + TEXT("_training_dummy_"))
                    || !Row->TryGetStringField(TEXT("name"), Result.Name) || Result.Name.IsEmpty()
                    || !Number(Row, TEXT("level"), Level, 100) || FMath::FloorToDouble(Level) != Level
                    || !Number(Row, TEXT("maxHealth"), Health, 1000000)
                    || !Row->TryGetNumberField(TEXT("aggroRange"), Aggro) || Aggro != 0
                    || (Row->HasField(TEXT("model")) && (!Row->TryGetStringField(TEXT("model"), AuthoredModel) || AuthoredModel != Model))) return false;
                Result.bTrainingDummy = true; Result.StaticModel = Model;
                Result.Level = int32(Level); Result.MaxHealth = Health;
                continue;
            }
            double Level, Health, Aggro, Range, Preferred, Damage, Speed;
            if (++Matches != 1 || Row->HasField(TEXT("encounter"))
                || !Row->TryGetStringField(TEXT("archetype"), Archetype) || Archetype != TEXT("raider")
                || !Row->TryGetStringField(TEXT("characterProfileKey"), Profile) || FName(*Profile).IsNone()
                || !Row->TryGetStringField(TEXT("name"), Result.Name) || Result.Name.IsEmpty()
                || !Number(Row, TEXT("level"), Level, 100) || FMath::FloorToDouble(Level) != Level
                || !Number(Row, TEXT("maxHealth"), Health, 1000000)
                || !Number(Row, TEXT("aggroRange"), Aggro, 100)
                || !Number(Row, TEXT("attackRange"), Range, 10)
                || !Number(Row, TEXT("preferredRange"), Preferred, Range)
                || !Number(Row, TEXT("attackDamage"), Damage, 100000) || FMath::FloorToDouble(Damage) != Damage
                || !Number(Row, TEXT("moveSpeed"), Speed, 20)) return false;
            Result.Profile = FName(*Profile); Result.Level = int32(Level); Result.MaxHealth = Health;
            Result.AggroRange = Aggro * 100; Result.AttackRange = Range * 100;
            Result.PreferredRange = Preferred * 100; Result.AttackDamage = int32(Damage); Result.MoveSpeed = Speed * 100;
        }
    }
    if (Matches != 1) return false;
    Out = MoveTemp(Result); Error.Reset(); return true;
}

bool WarEnemies::CanEngage(bool bAlive, bool bVisible, FName EnemyZone, FName PlayerZone,
    double DistanceSquared, double HeightDifference, double Range)
{
    return bAlive && bVisible && !EnemyZone.IsNone() && EnemyZone == PlayerZone
        && FMath::IsFinite(DistanceSquared) && DistanceSquared >= 0 && FMath::IsFinite(Range) && Range > 0
        && DistanceSquared <= FMath::Square(Range) && FMath::IsFinite(HeightDifference) && FMath::Abs(HeightDifference) < 200;
}
