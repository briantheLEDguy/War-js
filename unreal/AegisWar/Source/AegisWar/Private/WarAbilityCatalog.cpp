#include "WarAbilityCatalog.h"
#include "WarContentSubsystem.h"
#include "WarAbilityConditions.h"
#include "WarAbilityWorkshopDocument.h"
#include "Engine/World.h"
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

bool WarAbilities::Parse(const TSharedPtr<const FJsonObject>& Manifest, TArray<FWarAbilityDefinition>& Out, FString& Error,bool bAllowEmpty)
{
    Out.Reset(); Error.Reset();
    const auto Source = Object(Manifest, TEXT("abilities"));
    TMap<FName, int32> Unlocks;
    for (const auto& Value : Array(Source, TEXT("progression")))
    { const auto Row = Value->AsObject(); Unlocks.Add(FName(*String(Row, TEXT("abilityId"))), Number(Row, TEXT("unlockLevel"))); }
    TSet<FString> Ids;
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
            if (Row->HasTypedField<EJson::String>(TEXT("runtimeCareer"))) A.Career=FName(*String(Row,TEXT("runtimeCareer")));
            A.AssignmentId=FName(*String(Row,TEXT("assignmentId"))); A.Version=TEXT("baseline");
            Row->TryGetBoolField(TEXT("legacyTargeting"),A.bLegacyTargeting);
            Row->TryGetBoolField(TEXT("authoredTiming"),A.bAuthoredTiming);
            A.Name = String(Row, TEXT("name")); A.Summary = String(Row, TEXT("summary"));
            A.UnavailableReason = String(Row, TEXT("unavailableReason"));
            A.Slot = Number(Row, TEXT("slot"), -1); A.UnlockLevel = Number(Row,TEXT("unlockLevel"),Unlocks.FindRef(A.Id));
            A.Shape = FName(*String(Target, TEXT("shape"))); A.bEnemyTarget = String(Target, TEXT("target")) == TEXT("enemy");
            A.TargetKind=FName(*String(Target,TEXT("target"))); A.MaxTargets=Number(Target,TEXT("maxTargets"),128);
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
                Effect.Id=FName(*String(E,TEXT("id")));
                if (Effect.Id.IsNone()) Effect.Id=FName(*FString::Printf(TEXT("effect_%d"),A.Effects.Num()+1));
                Effect.Kind = FName(*String(E, TEXT("kind"))); Effect.School = FName(*String(E, TEXT("school")));
                Effect.Recipient=FName(*String(E,TEXT("recipient")));
                const auto Periodic=Object(E,TEXT("periodic")); Effect.PeriodicDuration=Number(Periodic,TEXT("durationSec")); Effect.Interval=Number(Periodic,TEXT("intervalSec"),1);
                Effect.Minimum = Number(Amount, TEXT("min")); Effect.Maximum = Number(Amount, TEXT("max"));
                Effect.bHasAmount=Amount.IsValid();
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
                if (!TArray<FName>{TEXT("damage"), TEXT("heal"), TEXT("status"), TEXT("player_status"), TEXT("movement"), TEXT("cleanse"), TEXT("wrath_relic")}.Contains(Effect.Kind)
                    || (Effect.Kind == TEXT("wrath_relic") && A.Id != TEXT("battle_prelate.icon_of_wrath")))
                { Error = TEXT("Unsupported ability effect: ") + Id; Out.Reset(); return false; }
                A.Effects.Add(Effect);
            }
            if (!WarAbilityConditions::ParseRules(Row,A.Conditions,Error)) { Out.Reset(); return false; }
            const auto Timing=Object(Row,TEXT("timing")); A.TimingMode=FName(*String(Timing,TEXT("mode")));
            A.CastSeconds=Number(Timing,TEXT("castSec")); A.ChannelSeconds=Number(Timing,TEXT("channelSec")); A.TickInterval=Number(Timing,TEXT("intervalSec"),1);
            const auto Presentations=Object(Row,TEXT("presentations"));
            if (Presentations) for (const auto& Entry : Presentations->Values) A.Presentations.Add(FName(*Entry.Key),FName(*Entry.Value->AsString()));
            const FString Identity=A.Career.ToString()+TEXT(":")+Id;
            if (A.Career.IsNone() || (A.AssignmentId.IsNone() && (Career.IsEmpty() || Suffix.IsEmpty())) || Ids.Contains(Identity) || A.Slot < 0 || (A.AssignmentId.IsNone() && Slots.Contains(A.Slot))
                || A.UnlockLevel < 1 || A.ResourceMax <= 0 || (A.Effects.IsEmpty() && A.UnavailableReason.IsEmpty()))
            { Error = TEXT("Invalid or duplicate class ability: ") + Id; Out.Reset(); return false; }
            Ids.Add(Identity); Slots.Add(A.Slot); Out.Add(MoveTemp(A));
        }
    }
    if (Out.IsEmpty() && !bAllowEmpty) { Error = TEXT("Class ability catalog is missing."); return false; }
    return true;
}

FName WarAbilities::Motion(const FWarAbilityDefinition& A, FName Profile)
{
    if (const auto* Binding=A.Presentations.Find(Profile)) return *Binding;
    // The approved playable profiles bind every ability ID to an authored recipe.
    // Other, unimplemented profiles cannot inherit their equipment corrections.
    if ((A.Career == TEXT("battle_prelate") && Profile == TEXT("civic_battle_prelate_m"))
        || (A.Career == TEXT("sunfire_templar") && Profile == TEXT("civic_sunfire_templar_m"))
        || (A.Career == TEXT("warbrute") && Profile == TEXT("mire_warbrute_m"))
        || (A.Career == TEXT("ember_arcanist") && Profile == TEXT("civic_ember_arcanist_m"))) return A.Id;
    return A.Shape == TEXT("melee") || A.Shape == TEXT("dash") ? TEXT("attack_melee")
        : A.School == TEXT("physical") ? TEXT("attack_ranged") : TEXT("cast");
}
float WarAbilities::ReleaseFraction(const FWarAbilityDefinition& A, FName Profile)
{
    // Native profiles use their measured AbilityPresentations.ContactSeconds.
    return A.ReleaseFraction;
}
float WarAbilities::Amount(const FWarAbilityEffect& E, float Strength, int32 Level, float Spent, float Random)
{ return FMath::Max(1.f,FMath::RoundToFloat(RawAmount(E,Strength,Level,Spent,Random))); }
float WarAbilities::RawAmount(const FWarAbilityEffect& E,float Strength,int32 Level,float Spent,float Random)
{ return FMath::Lerp(E.Minimum,E.Maximum,FMath::Clamp(Random,0.f,1.f))+E.StatScale*Strength+E.LevelScale*Level+E.ResourceScale*Spent; }
float WarAbilities::ResourceAfter(const FWarAbilityDefinition& A, float Current)
{ return FMath::Clamp((A.bSpendAll ? 0 : Current - A.Cost) + A.Build, 0.f, A.ResourceMax); }

void UWarAbilityCatalog::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection); Collection.InitializeDependency<UWarContentSubsystem>();
    WarAbilities::Parse(GetGameInstance()->GetSubsystem<UWarContentSubsystem>()->GetInterfaceCatalogSource(), Definitions, Error);
    if (!Error.IsEmpty()) UE_LOG(LogTemp, Error, TEXT("WAR_ABILITY_CATALOG: %s"), *Error);
    TickBoundary=FWorldDelegates::OnWorldTickStart.AddUObject(this,&UWarAbilityCatalog::ActivateStaged);
}
void UWarAbilityCatalog::Deinitialize()
{ FWorldDelegates::OnWorldTickStart.Remove(TickBoundary); Super::Deinitialize(); }
bool UWarAbilityCatalog::StageWorkspace(const FString& Json,const FString& InVersion,FString& OutError)
{
    if (InVersion.IsEmpty() || InVersion.Len()>120 || !StagedVersion.IsEmpty()) { OutError=TEXT("A version is already staged or has an invalid identity."); return false; }
    TArray<FWarAbilityDefinition> Candidate,Library;
    if (!FWarAbilityWorkshopDocument::Compile(WarWorkshopJson::Parse(Json),Candidate,OutError,&Library)) return false;
    StagedDefinitions=MoveTemp(Candidate); StagedLibrary=MoveTemp(Library); StagedDocument=Json; StagedVersion=InVersion; return true;
}
void UWarAbilityCatalog::ActivateStaged(UWorld* World,ELevelTick Tick,float Delta)
{
    if (StagedVersion.IsEmpty() || !World || World->GetGameInstance()!=GetGameInstance()) return;
    FString Failure;
    if (Install(StagedDefinitions,StagedVersion,Failure,&StagedLibrary)) ActiveDocument=MoveTemp(StagedDocument);
    else UE_LOG(LogTemp,Error,TEXT("Ability version rejected at activation: %s"),*Failure);
    StagedVersion.Reset(); StagedDocument.Reset(); StagedDefinitions.Reset(); StagedLibrary.Reset();
}
void UWarAbilityCatalog::CancelStaged(const FString& InVersion)
{
    if (StagedVersion!=InVersion) return;
    StagedVersion.Reset(); StagedDocument.Reset(); StagedDefinitions.Reset(); StagedLibrary.Reset();
}
const FWarAbilityDefinition* UWarAbilityCatalog::Find(FName Id, FName Career) const
{ return Definitions.FindByPredicate([Id,Career](const auto& A) { return A.Id == Id && (Career.IsNone() || A.Career==Career); }); }
TArray<const FWarAbilityDefinition*> UWarAbilityCatalog::Kit(FName Career) const
{
    TArray<const FWarAbilityDefinition*> Result;
    for (const auto& A : Definitions) if (A.Career == Career) Result.Add(&A);
    Result.Sort([](const auto& A, const auto& B) { return A.Slot < B.Slot; }); return Result;
}
bool UWarAbilityCatalog::Install(const TArray<FWarAbilityDefinition>& Candidate, const FString& InVersion, FString& OutError,const TArray<FWarAbilityDefinition>* Library)
{
    if (InVersion.IsEmpty()) { OutError=TEXT("A version identity is required."); return false; }
    TSet<FString> Identities;
    for (const auto& A : Candidate)
    {
        const FString Key=A.Career.ToString()+TEXT(":")+A.Id.ToString();
        if (Identities.Contains(Key) || !WarAbilityConditions::Validate(A,Library ? *Library : Candidate,OutError))
        { if (OutError.IsEmpty()) OutError=TEXT("Duplicate class assignment."); return false; }
        Identities.Add(Key);
    }
    Definitions=Candidate; Version=InVersion;
    for (auto& A : Definitions) A.Version=Version;
    Error.Reset(); return true;
}
