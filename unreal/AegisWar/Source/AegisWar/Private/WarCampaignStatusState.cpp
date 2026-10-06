#include "WarCombatStatus.h"
#include "WarCampaignCombatState.h"
#include "WarCampaignCombatDefinition.h"
#include "WarCharacter.h"
#include "WarPlayerState.h"
#include "Engine/GameInstance.h"
#include "Dom/JsonObject.h"

namespace
{
    FString Name(FName Value) { return Value.IsNone() ? FString() : Value.ToString(); }
    const FWarAbilityEffect* AppliedEffect(const FWarAbilityDefinition& Ability,FName Id)
    {
        if (const auto* Effect=Ability.Effects.FindByPredicate([&](const auto& E) { return E.Id==Id; })) return Effect;
        for (const auto& Rule:Ability.Conditions) for (const auto& Action:Rule.Actions)
            if (Action.Kind==TEXT("add_effect") && Action.Effect.Id==Id) return &Action.Effect;
        return nullptr;
    }
    FName EngineId(const FWarAbilityDefinition& Ability,const FWarAbilityEffect& Effect,const FString& Source)
    {
        return FName(*(!Effect.Recipient.IsNone() || Effect.PeriodicDuration>0
            ? Ability.Id.ToString()+TEXT(":")+Effect.Id.ToString()+TEXT(":")+Source
            : Ability.Id.ToString()+TEXT(":")+Effect.StatusId.ToString()+TEXT(":")+Effect.StatusKind.ToString()));
    }
    bool String(const TSharedPtr<FJsonObject>& Row,const TCHAR* Field,FString& Out,int32 Limit=1024,bool Empty=true,bool Prose=false)
    {
        if (!Row || !Row->HasTypedField<EJson::String>(Field) || !Row->TryGetStringField(Field,Out) || Out.Len()>Limit || (!Empty && Out.IsEmpty())) return false;
        for (TCHAR C:Out) if ((C<32 && !(Prose && (C=='\n' || C=='\r' || C=='\t'))) || C==127) return false;
        return true;
    }
}
bool UWarCombatStatus::CaptureCampaignState(int64 CapturedAt,TSharedPtr<FJsonObject>& State,FString& Error) const
{
    using namespace WarCampaignCombatState;
    State=nullptr; auto Result=MakeShared<FJsonObject>(); Result->SetNumberField(TEXT("version"),1);
    TArray<TSharedPtr<FJsonValue>> Definitions,Statuses; TSet<FString> Hashes;
    TMap<const FWarAbilityDefinition*,TPair<FString,FString>> Encoded;
    const double WorldNow=Now();
    for (const auto& S:Active)
    {
        if (S.Expires<=WorldNow || (S.Kind==TEXT("shield") && S.Shield<=0)) continue;
        const auto* Definition=AppliedDefinitions.Find(S.Id); const auto* Source=SourceKeys.Find(S.Id);
        if (!Definition || !*Definition || !Source || !ValidKey(*Source) || (*Definition)->Id!=S.AbilityId || (*Definition)->Version!=S.AppliedVersion
            || !AppliedEffect(**Definition,S.EffectId))
        { Error=TEXT("An active status lacks its exact applied definition or durable source. Custody remains protected until expiry."); return false; }
        FString Payload,Hash;
        if (const auto* Cached=Encoded.Find(Definition->Get())) { Payload=Cached->Key; Hash=Cached->Value; }
        else
        {
            if (!WarCampaignCombatDefinition::Encode(**Definition,Payload,Hash,Error)) return false;
            Encoded.Add(Definition->Get(),TPair<FString,FString>(Payload,Hash));
        }
        if (!Hashes.Contains(Hash))
        {
            auto DefinitionRow=MakeShared<FJsonObject>(); DefinitionRow->SetStringField(TEXT("id"),Name((*Definition)->Id));
            DefinitionRow->SetStringField(TEXT("career"),Name((*Definition)->Career)); DefinitionRow->SetStringField(TEXT("version"),(*Definition)->Version);
            DefinitionRow->SetStringField(TEXT("payload"),Payload); DefinitionRow->SetStringField(TEXT("sha256"),Hash);
            Definitions.Add(MakeShared<FJsonValueObject>(DefinitionRow)); Hashes.Add(Hash);
        }
        auto Row=MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("id"),EngineId(**Definition,*AppliedEffect(**Definition,S.EffectId),*Source).ToString());
        Row->SetStringField(TEXT("kind"),Name(S.Kind)); Row->SetStringField(TEXT("group"),Name(S.Group)); Row->SetStringField(TEXT("modifier"),Name(S.Modifier));
        Row->SetStringField(TEXT("label"),S.Label); Row->SetStringField(TEXT("sourceKey"),*Source); Row->SetStringField(TEXT("sourceRealm"),Name(S.SourceRealm));
        Row->SetStringField(TEXT("abilityId"),Name(S.AbilityId)); Row->SetStringField(TEXT("effectId"),Name(S.EffectId)); Row->SetStringField(TEXT("category"),Name(S.Category));
        Row->SetStringField(TEXT("appliedVersion"),S.AppliedVersion); Row->SetStringField(TEXT("definitionSha256"),Hash);
        Row->SetNumberField(TEXT("magnitude"),S.Magnitude); Row->SetNumberField(TEXT("shield"),S.Shield); Row->SetNumberField(TEXT("tickDamage"),S.TickDamage);
        Row->SetNumberField(TEXT("tickHealing"),S.TickHealing); Row->SetNumberField(TEXT("interval"),S.Interval);
        if (S.ExpiresAtUnixMs<=0 || !FMath::IsFinite(S.NextTickUnixMs) || S.NextTickUnixMs<0)
        { Error=TEXT("An active status lacks its original fixed custody deadlines.");return false; }
        Row->SetNumberField(TEXT("expiresAtUnixMs"),S.ExpiresAtUnixMs);
        Row->SetNumberField(TEXT("nextTickAtUnixMs"),FMath::Max<int64>(0,FMath::RoundToInt64(S.NextTickUnixMs)));
        if (const auto* Execution=Periodic.Find(S.Id))
        {
            const auto* Target=TargetKeys.Find(S.Id);
            if (!Target || !ValidKey(*Target,true)) { Error=TEXT("A periodic effect selected target has no durable identity."); return false; }
            auto Period=MakeShared<FJsonObject>(); Period->SetNumberField(TEXT("base"),Execution->Base); Period->SetNumberField(TEXT("strength"),Execution->Strength);
            Period->SetNumberField(TEXT("level"),Execution->Level); Period->SetBoolField(TEXT("bonus"),Execution->bBonus); Period->SetStringField(TEXT("targetKey"),*Target);
            Row->SetObjectField(TEXT("periodic"),Period);
        }
        Statuses.Add(MakeShared<FJsonValueObject>(Row));
    }
    Result->SetArrayField(TEXT("definitions"),Definitions); Result->SetArrayField(TEXT("statuses"),Statuses);
    // Validate our own pure snapshot before it becomes a successful durable character mutation.
    if (!const_cast<UWarCombatStatus*>(this)->RestoreCampaignState(Result,CapturedAt,Error,false)) return false;
    State=Result; return true;
}
bool UWarCombatStatus::RestoreCampaignState(const TSharedPtr<FJsonObject>& State,int64 CurrentUtc,FString& Error,bool bApply,bool ClearForRespawn)
{
    using namespace WarCampaignCombatState;
    const TArray<TSharedPtr<FJsonValue>>* DefinitionRows=nullptr; const TArray<TSharedPtr<FJsonValue>>* StatusRows=nullptr; double Version=0;
    if (!GetOwner()->HasAuthority() || !Number(State,TEXT("version"),Version,1,1) || !State->TryGetArrayField(TEXT("definitions"),DefinitionRows)
        || !State->TryGetArrayField(TEXT("statuses"),StatusRows) || DefinitionRows->Num()>128 || StatusRows->Num()>128)
    { Error=TEXT("Invalid bounded combat snapshot."); return false; }
    TMap<FString,TSharedPtr<const FWarAbilityDefinition>> Definitions; TSet<FString> Identities; TArray<FWarAbilityDefinition> Library;
    for (const auto& Value:*DefinitionRows)
    {
        const auto Row=Value.IsValid() && Value->Type==EJson::Object ? Value->AsObject() : nullptr;
        FString Id,Career,VersionString,Payload,Hash; FWarAbilityDefinition Definition;
        if (!Row || Row->Values.Num()!=5 || !String(Row,TEXT("id"),Id,160,false) || !String(Row,TEXT("career"),Career,160,false)
            || !String(Row,TEXT("version"),VersionString,160,false) || !Row->HasTypedField<EJson::String>(TEXT("payload")) || !Row->TryGetStringField(TEXT("payload"),Payload)
            || !String(Row,TEXT("sha256"),Hash,64,false) || !WarCampaignCombatDefinition::Decode(Payload,Hash,Definition,Error)
            || Name(Definition.Id)!=Id || Name(Definition.Career)!=Career || Definition.Version!=VersionString || Definitions.Contains(Hash)
            || Identities.Contains(Career+TEXT(":")+Id+TEXT(":")+VersionString))
        { if (Error.IsEmpty()) Error=TEXT("Applied combat definition identity is invalid."); return false; }
        Identities.Add(Career+TEXT(":")+Id+TEXT(":")+VersionString); Library.Add(Definition);
        Definitions.Add(Hash,MakeShared<const FWarAbilityDefinition>(MoveTemp(Definition)));
    }
    if (auto* Instance=GetWorld()->GetGameInstance()) if (auto* Catalog=Instance->GetSubsystem<UWarAbilityCatalog>()) Library.Append(Catalog->All());
    for (const auto& Pair:Definitions)
    {
        // The recorded applied version governs self references even after a catalog edit.
        TArray<FWarAbilityDefinition> AppliedLibrary; AppliedLibrary.Add(*Pair.Value); AppliedLibrary.Append(Library);
        if (!WarAbilityConditions::Validate(*Pair.Value,AppliedLibrary,Error)) return false;
    }
    TArray<FWarActiveStatus> Restored; TMap<FName,FPeriodicExecution> RestoredPeriodic;
    TMap<FName,TSharedPtr<const FWarAbilityDefinition>> RestoredDefinitions; TMap<FName,FString> RestoredSources,RestoredTargets; TSet<FString> StatusIds;
    const double WorldNow=Now();
    for (const auto& Value:*StatusRows)
    {
        const auto Row=Value.IsValid() && Value->Type==EJson::Object ? Value->AsObject() : nullptr;
        FString Id,Kind,Group,Modifier,Label,SourceKey,Realm,AbilityId,EffectId,Category,AppliedVersion,Hash;
        double Magnitude=0,Shield=0,Damage=0,Healing=0,Interval=0,Expiry=0,NextTick=0;
        if (!Row || (Row->Values.Num()!=19 && Row->Values.Num()!=20) || !String(Row,TEXT("id"),Id,1024,false) || StatusIds.Contains(Id)
            || !String(Row,TEXT("kind"),Kind,160,false) || !String(Row,TEXT("group"),Group,160) || !String(Row,TEXT("modifier"),Modifier,160)
            || !String(Row,TEXT("label"),Label,512,true,true) || !String(Row,TEXT("sourceKey"),SourceKey,512,false) || !ValidKey(SourceKey)
            || !String(Row,TEXT("sourceRealm"),Realm,160) || !(Realm.IsEmpty() || Realm==TEXT("aegis") || Realm==TEXT("riftbound"))
            || !String(Row,TEXT("abilityId"),AbilityId,160,false) || !String(Row,TEXT("effectId"),EffectId,160,false)
            || !String(Row,TEXT("category"),Category,160,false) || !String(Row,TEXT("appliedVersion"),AppliedVersion,160,false) || !String(Row,TEXT("definitionSha256"),Hash,64,false)
            || !Number(Row,TEXT("magnitude"),Magnitude,0,1) || !Number(Row,TEXT("shield"),Shield,0,MAX_flt) || !Number(Row,TEXT("tickDamage"),Damage,0,MAX_flt)
            || !Number(Row,TEXT("tickHealing"),Healing,0,MAX_flt) || !Number(Row,TEXT("interval"),Interval,.1,60)
            || !Epoch(Row,TEXT("expiresAtUnixMs"),Expiry) || !Epoch(Row,TEXT("nextTickAtUnixMs"),NextTick))
        { Error=TEXT("Invalid combat status values or durable source key."); return false; }
        StatusIds.Add(Id); const auto Definition=Definitions.FindRef(Hash);
        const auto* Effect=Definition ? AppliedEffect(*Definition,FName(*EffectId)) : nullptr;
        if (!Effect || Name(Definition->Id)!=AbilityId || Definition->Version!=AppliedVersion || EngineId(*Definition,*Effect,SourceKey).ToString()!=Id
            || !(Category==TEXT("status") || Category==TEXT("shield") || Category==TEXT("dot") || Category==TEXT("hot")))
        { Error=TEXT("Status does not match its immutable applied effect."); return false; }
        const bool PeriodicEffect=Effect->PeriodicDuration>0;
        const FString ExpectedCategory=PeriodicEffect ? (Effect->Kind==TEXT("heal") ? TEXT("hot") : TEXT("dot"))
            : Kind==TEXT("shield") ? TEXT("shield") : Kind==TEXT("burn") || Kind==TEXT("bleed") ? TEXT("dot") : TEXT("status");
        if (Category!=ExpectedCategory || (PeriodicEffect && (Kind!=ExpectedCategory || Interval!=Effect->Interval || !Group.IsEmpty() || !Modifier.IsEmpty() || Magnitude!=0 || Shield!=0))
            || (!PeriodicEffect && (Kind!=Name(Effect->StatusKind) || Group!=Name(Effect->StackGroup) || Modifier!=Name(Effect->Modifier))))
        { Error=TEXT("Status kind/group or periodic cadence differs from its applied definition."); return false; }
        const TSharedPtr<FJsonObject>* Period=nullptr; const bool HasPeriod=Row->TryGetObjectField(TEXT("periodic"),Period);
        FPeriodicExecution Execution; FString TargetKey; double Base=0,Strength=0,Level=0; bool Bonus=false;
        if (HasPeriod!=PeriodicEffect || (HasPeriod && ((*Period)->Values.Num()!=5 || !Number(*Period,TEXT("base"),Base,0,MAX_flt)
            || !Number(*Period,TEXT("strength"),Strength) || !Number(*Period,TEXT("level"),Level,1,1000) || Level!=FMath::FloorToDouble(Level)
            || !(*Period)->HasTypedField<EJson::Boolean>(TEXT("bonus")) || !(*Period)->TryGetBoolField(TEXT("bonus"),Bonus) || !String(*Period,TEXT("targetKey"),TargetKey,512) || !ValidKey(TargetKey,true))))
        { Error=TEXT("Invalid periodic execution snapshot."); return false; }
        if (Expiry<=CurrentUtc || ClearForRespawn || (Kind==TEXT("shield") && Shield<=0)) continue;
        if ((Expiry-CurrentUtc)>(PeriodicEffect ? Effect->PeriodicDuration : Effect->Duration)*1000.+1)
        { Error=TEXT("Status duration exceeds the bounded applied lifetime."); return false; }
        auto* Source=Cast<AWarCharacter>(Resolve(GetWorld(),SourceKey)); auto* Target=TargetKey.IsEmpty() ? nullptr : Resolve(GetWorld(),TargetKey);
        if (!Source || (!TargetKey.IsEmpty() && !Target)) { Error=TEXT("An unexpired effect awaits its original live source or target. Recovery remains protected."); return false; }
        if (const auto* PS=Source->GetPlayerState<AWarPlayerState>())
        { const FString ActualRealm=PS->GetRealm()==EWarRealm::Aegis ? TEXT("aegis") : PS->GetRealm()==EWarRealm::Riftbound ? TEXT("riftbound") : TEXT("");
            if (ActualRealm!=Realm) { Error=TEXT("Recovered effect source realm changed."); return false; } }
        FWarActiveStatus S; S.Id=EngineId(*Definition,*Effect,Source->GetPathName()); S.Kind=FName(*Kind); S.Group=FName(*Group); S.Modifier=FName(*Modifier); S.Label=Label;
        S.Magnitude=Magnitude; S.Shield=Shield; S.TickDamage=Damage; S.TickHealing=Healing; S.Interval=Interval; S.Expires=WorldNow+(Expiry-CurrentUtc)/1000.;
        // Advance cadence past every offline tick without applying damage, healing or rewards.
        if (NextTick<=CurrentUtc) NextTick+=(FMath::FloorToDouble((CurrentUtc-NextTick)/(Interval*1000.))+1)*Interval*1000.;
        S.NextTick=WorldNow+(NextTick-CurrentUtc)/1000.;S.ExpiresAtUnixMs=int64(Expiry);S.NextTickUnixMs=NextTick;
        S.Source=Source; S.SourceCombatant=FName(*Source->GetPathName()); S.SourceRealm=FName(*Realm);
        S.AbilityId=FName(*AbilityId); S.EffectId=FName(*EffectId); S.Category=FName(*Category); S.AppliedVersion=AppliedVersion;
        if (Restored.ContainsByPredicate([&](const auto& Existing) { return Existing.Id==S.Id; })) { Error=TEXT("Restored status identity collides."); return false; }
        Restored.Add(S); RestoredDefinitions.Add(S.Id,Definition); RestoredSources.Add(S.Id,SourceKey);
        if (HasPeriod)
        {
            Execution.Ability=Definition; Execution.Effect=*Effect; Execution.Target=Target; Execution.Base=Base; Execution.Strength=Strength; Execution.Level=Level; Execution.bBonus=Bonus;
            RestoredPeriodic.Add(S.Id,MoveTemp(Execution)); RestoredTargets.Add(S.Id,TargetKey);
        }
    }
    if (bApply)
    { Active=MoveTemp(Restored); Periodic=MoveTemp(RestoredPeriodic); AppliedDefinitions=MoveTemp(RestoredDefinitions); SourceKeys=MoveTemp(RestoredSources); TargetKeys=MoveTemp(RestoredTargets); GetOwner()->ForceNetUpdate(); }
    return true;
}
