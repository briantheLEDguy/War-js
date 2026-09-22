#include "WarAbilityCatalog.h"
#include "WarContentSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"

namespace
{
    float Number(const TSharedPtr<const FJsonObject>& Object, const TCHAR* Key, float Default = 0)
    { double Value; return Object.IsValid() && Object->TryGetNumberField(Key, Value) ? static_cast<float>(Value) : Default; }
    FString String(const TSharedPtr<const FJsonObject>& Object, const TCHAR* Key)
    { FString Value; if (Object) Object->TryGetStringField(Key, Value); return Value; }
    TSharedPtr<FJsonObject> Object(const TSharedPtr<const FJsonObject>& Parent, const TCHAR* Key)
    { const TSharedPtr<FJsonObject>* Value; return Parent && Parent->TryGetObjectField(Key, Value) ? *Value : nullptr; }
    const TArray<TSharedPtr<FJsonValue>>& Array(const TSharedPtr<const FJsonObject>& Parent, const TCHAR* Key)
    { static const TArray<TSharedPtr<FJsonValue>> Empty; const TArray<TSharedPtr<FJsonValue>>* Value;
      return Parent && Parent->TryGetArrayField(Key, Value) ? *Value : Empty; }
}

bool WarAbilities::Parse(const TSharedPtr<const FJsonObject>& Manifest, TArray<FWarAbilityDefinition>& Out, FString& Error)
{
    Out.Reset(); Error.Reset();
    const auto Source = Object(Manifest, TEXT("abilities"));
    TMap<FName, int32> Unlocks;
    for (const auto& Value : Array(Source, TEXT("progression")))
    { const auto Row = Value->AsObject(); Unlocks.Add(FName(*String(Row, TEXT("abilityId"))), Number(Row, TEXT("unlockLevel"))); }
    TSet<FName> Ids;
    for (const auto& KitValue : Array(Source, TEXT("kits")))
    {
        const auto Kit = KitValue->AsObject(), Resource = Object(Kit, TEXT("resource"));
        TSet<int32> Slots;
        for (const auto& Value : Array(Kit, TEXT("abilities")))
        {
            const auto Row = Value->AsObject(), Target = Object(Row, TEXT("targeting")), Cost = Object(Row, TEXT("resource"));
            FWarAbilityDefinition A;
            const FString Id = String(Row, TEXT("id")); FString Career, Suffix;
            Id.Split(TEXT("."), &Career, &Suffix); A.Id = FName(*Id); A.Career = FName(*Career);
            A.Name = String(Row, TEXT("name")); A.Summary = String(Row, TEXT("summary"));
            A.UnavailableReason = String(Row, TEXT("unavailableReason"));
            A.Slot = Number(Row, TEXT("slot"), -1); A.UnlockLevel = Unlocks.FindRef(A.Id);
            A.Shape = FName(*String(Target, TEXT("shape"))); A.bEnemyTarget = String(Target, TEXT("target")) == TEXT("enemy");
            A.Range = Number(Target, TEXT("range")) * 100; A.Radius = Number(Target, TEXT("radius")) * 100;
            A.ProjectileSpeed = Number(Target, TEXT("projectileSpeed")) * 100;
            A.Cooldown = Number(Row, TEXT("cooldownSec")); A.Gcd = Number(Row, TEXT("gcdSec"));
            A.Mana = Number(Cost, TEXT("manaCost")); A.Cost = Number(Cost, TEXT("careerCost"));
            A.Build = Number(Cost, TEXT("careerBuild")); A.MinimumResource = Number(Cost, TEXT("minCareer"));
            if (Cost) Cost->TryGetBoolField(TEXT("spendAllCareer"), A.bSpendAll);
            A.ResourceLabel = String(Resource, TEXT("label")); A.ResourceMax = Number(Resource, TEXT("max"));
            A.ResourceInitial = Number(Resource, TEXT("initial"));
            A.School = FName(*String(Object(Row, TEXT("visual")), TEXT("school")));
            for (const auto& Tag : Array(Object(Row, TEXT("cancelRules")), TEXT("blockedBy")))
                A.bBlockedBySilence |= Tag->AsString() == TEXT("State.Silenced");
            const auto Animation = Object(Row, TEXT("animation"));
            const float Duration = Number(Animation, TEXT("durationSec"), 1);
            A.ReleaseFraction = FMath::Clamp(Number(Animation, TEXT("contactSec"), Duration * .4f) / FMath::Max(.01f, Duration), .05f, .95f);
            for (const auto& EffectValue : Array(Row, TEXT("effects")))
            {
                const auto E = EffectValue->AsObject(), Amount = Object(E, TEXT("amount")); FWarAbilityEffect Effect;
                Effect.Kind = FName(*String(E, TEXT("kind"))); Effect.School = FName(*String(E, TEXT("school")));
                Effect.Minimum = Number(Amount, TEXT("min")); Effect.Maximum = Number(Amount, TEXT("max"));
                Effect.StatScale = Number(Amount, TEXT("statScale")); Effect.LevelScale = Number(Amount, TEXT("levelScale"));
                Effect.ResourceScale = Number(Amount, TEXT("resourceScale"));
                const auto Status = Object(E, Effect.Kind == TEXT("player_status") ? TEXT("playerStatus") : TEXT("status"));
                Effect.StatusId = FName(*String(Status, TEXT("id"))); Effect.StatusKind = FName(*String(Status, TEXT("kind")));
                Effect.Label = String(Status, TEXT("label")); Effect.Duration = Number(Status, TEXT("durationSec"));
                Effect.Magnitude = Number(Status, TEXT("magnitude"), Effect.StatusKind == TEXT("slow") ? .3f : .15f);
                Effect.Modifier = FName(*String(Status, TEXT("damageModifier"))); Effect.StackGroup = FName(*String(Status, TEXT("stackGroup")));
                const auto Movement = Object(E, TEXT("movement"));
                Effect.Direction = FName(*String(Movement, TEXT("mode"))); Effect.Distance = Number(Movement, TEXT("distance")) * 100;
                for (const auto& Kind : Array(Object(E, TEXT("cleanse")), TEXT("kinds"))) Effect.Cleanse.Add(FName(*Kind->AsString()));
                if (!TArray<FName>{TEXT("damage"), TEXT("heal"), TEXT("status"), TEXT("player_status"), TEXT("movement"), TEXT("cleanse")}.Contains(Effect.Kind))
                { Error = TEXT("Unsupported ability effect: ") + Id; Out.Reset(); return false; }
                A.Effects.Add(Effect);
            }
            if (Career.IsEmpty() || Suffix.IsEmpty() || Ids.Contains(A.Id) || A.Slot < 0 || A.Slot >= 10 || Slots.Contains(A.Slot)
                || A.UnlockLevel < 1 || A.ResourceMax <= 0 || (A.Effects.IsEmpty() && A.UnavailableReason.IsEmpty()))
            { Error = TEXT("Invalid or duplicate class ability: ") + Id; Out.Reset(); return false; }
            Ids.Add(A.Id); Slots.Add(A.Slot); Out.Add(MoveTemp(A));
        }
        if (Slots.Num() != 10) { Error = TEXT("A class kit must contain ten abilities."); Out.Reset(); return false; }
    }
    if (Out.IsEmpty()) { Error = TEXT("Class ability catalog is missing."); return false; }
    return true;
}

FName WarAbilities::Motion(const FWarAbilityDefinition& A, FName Profile)
{
    // Every Prelate action uses the equipped, grip-verified supplied set. Airborne,
    // sliding and long combination clips remain excluded from live combat.
    if (A.Career == TEXT("battle_prelate") && Profile == TEXT("civic_battle_prelate_m"))
        return TEXT("attack_melee"); // Holy invocations also have a visible hammer-led gesture.
    return A.Shape == TEXT("melee") || A.Shape == TEXT("dash") ? TEXT("attack_melee")
        : A.School == TEXT("physical") ? TEXT("attack_ranged") : TEXT("cast");
}
float WarAbilities::ReleaseFraction(const FWarAbilityDefinition& A, FName Profile)
{
    // Supplied 1.8 s slash reaches the forward contact at ~1.44 s (review frames
    // 42-45 at 30 Hz). The old procedural contact was still in this clip's windup.
    return A.Career == TEXT("battle_prelate") && Profile == TEXT("civic_battle_prelate_m") && Motion(A, Profile) == TEXT("attack_melee") ? .8f : A.ReleaseFraction;
}
float WarAbilities::Amount(const FWarAbilityEffect& E, float Strength, int32 Level, float Spent, float Random)
{ return FMath::Max(1.f, FMath::RoundToFloat(FMath::Lerp(E.Minimum, E.Maximum, FMath::Clamp(Random, 0.f, 1.f)) + E.StatScale * Strength + E.LevelScale * Level + E.ResourceScale * Spent)); }
float WarAbilities::ResourceAfter(const FWarAbilityDefinition& A, float Current)
{ return FMath::Clamp((A.bSpendAll ? 0 : Current - A.Cost) + A.Build, 0.f, A.ResourceMax); }

void UWarAbilityCatalog::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection); Collection.InitializeDependency<UWarContentSubsystem>();
    WarAbilities::Parse(GetGameInstance()->GetSubsystem<UWarContentSubsystem>()->GetInterfaceCatalogSource(), Definitions, Error);
    if (!Error.IsEmpty()) UE_LOG(LogTemp, Error, TEXT("WAR_ABILITY_CATALOG: %s"), *Error);
}
const FWarAbilityDefinition* UWarAbilityCatalog::Find(FName Id) const
{ return Definitions.FindByPredicate([Id](const auto& A) { return A.Id == Id; }); }
TArray<const FWarAbilityDefinition*> UWarAbilityCatalog::Kit(FName Career) const
{
    TArray<const FWarAbilityDefinition*> Result;
    for (const auto& A : Definitions) if (A.Career == Career) Result.Add(&A);
    Result.Sort([](const auto& A, const auto& B) { return A.Slot < B.Slot; }); return Result;
}
