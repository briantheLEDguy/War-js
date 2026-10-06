#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCampaignCombatState.h"
#include "WarCampaignCombatDefinition.h"
#include "WarCombatStatus.h"
#include "WarCampaignMutation.h"
#include "WarCampaignSiegeSubsystem.h"
#include "WarSiegeEncounter.h"
#include "WarSiegeGameMode.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarAbilityRuntime.h"
#include "WarAttributeSet.h"
#include "WarGameplayEffects.h"
#include "AbilitySystemComponent.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Misc/ScopeExit.h"
#include "HAL/PlatformProcess.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    TSharedPtr<FJsonObject> Copy(const TSharedPtr<FJsonObject>& State)
    { FString Text; FJsonSerializer::Serialize(State.ToSharedRef(),TJsonWriterFactory<>::Create(&Text)); TSharedPtr<FJsonObject> Result; FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Result); return Result; }
    FWarAbilityDefinition Definition()
    {
        FWarAbilityDefinition A; A.Id=TEXT("battle_prelate.custody"); A.Career=TEXT("battle_prelate"); A.Version=TEXT("applied-v1");
        A.Name=TEXT("Recorded custody"); A.TargetKind=TEXT("ally"); A.TimingMode=TEXT("instant"); A.bLegacyTargeting=false;
        FWarAbilityEffect Shield; Shield.Id=TEXT("shield"); Shield.Kind=TEXT("player_status"); Shield.Recipient=TEXT("caster");
        Shield.StatusId=TEXT("shield"); Shield.StatusKind=TEXT("shield"); Shield.Duration=30; Shield.Magnitude=.2f; Shield.StackGroup=TEXT("ward"); A.Effects.Add(Shield);
        FWarAbilityEffect Haste; Haste.Id=TEXT("haste"); Haste.Kind=TEXT("player_status"); Haste.Recipient=TEXT("caster");
        Haste.StatusId=TEXT("haste"); Haste.StatusKind=TEXT("haste"); Haste.Duration=20; Haste.Magnitude=.25f; A.Effects.Add(Haste);
        FWarAbilityEffect Hot; Hot.Id=TEXT("renew"); Hot.Kind=TEXT("heal"); Hot.Recipient=TEXT("target"); Hot.PeriodicDuration=12; Hot.Interval=.5f;
        Hot.Minimum=7; Hot.Maximum=7; Hot.bHasAmount=true; A.Effects.Add(Hot);
        FWarAbilityEffect Dot=Hot; Dot.Id=TEXT("scorch"); Dot.Kind=TEXT("damage"); Dot.Recipient=TEXT("target"); A.Effects.Add(Dot);
        FWarConditionalRule Rule; Rule.Id=TEXT("original_tick"); Rule.Event=TEXT("tick"); Rule.Condition.Kind=TEXT("all");
        FWarAbilityCondition HotCondition; HotCondition.Kind=TEXT("hot"); HotCondition.Subject=TEXT("recipient"); HotCondition.Source=TEXT("self");
        Rule.Condition.Children.Add(HotCondition);
        FWarConditionalAction Flat; Flat.Kind=TEXT("flat"); Flat.EffectId=Hot.Id; Flat.Value=3; Rule.Actions.Add(Flat); A.Conditions.Add(Rule);
        return A;
    }
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCampaignCombatStateTest,"AegisWar.Foundation.CampaignCombatState",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCampaignCombatStateTest::RunTest(const FString& Parameters)
{
    const auto Options=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Options);
    if (!World) return false; GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
    World->InitializeActorsForPlay(FURL());
    auto* PC=World->SpawnActor<AWarPlayerController>(); auto* PS=World->SpawnActor<AWarPlayerState>(); PC->PlayerState=PS; PS->SetOwner(PC);
    PC->ScenarioCharacterId=TEXT("stable-combat-custody"); PC->bCampaignIdentityProvisioned=true; PS->SetDevelopmentRealm(EWarRealm::Aegis);
    auto* Pawn=World->SpawnActor<AWarCharacter>(); Pawn->SetPlayerState(PS); PC->Possess(Pawn);
    auto* ASC=PS->GetAbilitySystemComponent(); ASC->InitAbilityActorInfo(PS,Pawn);
    ASC->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),100); ASC->SetNumericAttributeBase(UWarAttributeSet::GetMaxManaAttribute(),100);
    ASC->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),73); ASC->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),61);
    auto* Status=UWarCombatStatus::On(Pawn); if (!Status) return false;
    const auto Applied=MakeShared<const FWarAbilityDefinition>(Definition()); FString Error;
    FString AppliedPayload,AppliedSha;
    if (!TestTrue(TEXT("Fixture is a complete valid applied native definition"),WarCampaignCombatDefinition::Encode(*Applied,AppliedPayload,AppliedSha,Error)))
    { AddError(Error); return false; }
    Status->Apply(Applied->Effects[0],Applied->Id,Pawn,20,3,Applied->Version,-1,Applied);
    Status->ReceiveDamage(7); const float ShieldBefore=Status->GetActive()[0].Shield;
    Status->Apply(Applied->Effects[1],Applied->Id,Pawn,20,3,Applied->Version,-1,Applied);
    Status->ApplyPeriodic(Applied->Effects[2],7,Pawn,Pawn,Applied,20,3,false);
    Status->ApplyPeriodic(Applied->Effects[3],7,Pawn,nullptr,Applied,20,3,true);
    auto Cooldown=ASC->MakeOutgoingSpec(UWarStrikeCooldownEffect::StaticClass(),2,ASC->MakeEffectContext()); Cooldown.Data->SetDuration(9,true);
    Cooldown.Data->DynamicGrantedTags.AddTag(FGameplayTag::RequestGameplayTag(TEXT("War.Cooldown.DevelopmentStrike")));
    const auto OriginalCooldownHandle=ASC->ApplyGameplayEffectSpecToSelf(*Cooldown.Data.Get());int64 OriginalCooldownEpoch=0;
    TestTrue(TEXT("Actual native application event records the supported GAS handle"),PS->GetCampaignEffectEpoch(OriginalCooldownHandle,OriginalCooldownEpoch));
    auto Relative=MakeShared<FJsonObject>();Relative->SetNumberField(TEXT("globalCooldown"),4);
    auto SeedCooldown=MakeShared<FJsonObject>();SeedCooldown->SetStringField(TEXT("id"),TEXT("battle_prelate.custody"));SeedCooldown->SetNumberField(TEXT("remaining"),10);
    Relative->SetArrayField(TEXT("cooldowns"),{MakeShared<FJsonValueObject>(SeedCooldown)});PS->GetClassAbilities()->RestoreScenarioState(Relative);
    auto Saved=PS->CaptureCampaignState(Error);
    if (!TestNotNull(TEXT("Complete actual native status and cooldown capture"),Saved.Get())) { AddError(Error); return false; }
    const int64 Captured=Saved->GetNumberField(TEXT("capturedAtUnixMs")); const auto Combat=Saved->GetObjectField(TEXT("combat"));
    TestEqual(TEXT("Definitions deduplicate by exact applied payload"),Combat->GetArrayField(TEXT("definitions")).Num(),1);
    TestEqual(TEXT("Shield, buff, HOT and DOT are captured"),Combat->GetArrayField(TEXT("statuses")).Num(),4);
    TestEqual(TEXT("Known native ASC cooldown is captured"),Combat->GetArrayField(TEXT("ascEffects")).Num(),1);
    const double FrameTime=World->GetTimeSeconds();FPlatformProcess::SleepNoStats(.03f);
    auto Later=PS->CaptureCampaignState(Error);
    if (!TestNotNull(TEXT("A later real UTC capture in the same native frame succeeds"),Later.Get())) { AddError(Error);return false; }
    TestEqual(TEXT("The regression holds the actual game frame clock constant"),World->GetTimeSeconds(),FrameTime);
    TestTrue(TEXT("UTC advanced across actual capture work"),Later->GetNumberField(TEXT("capturedAtUnixMs"))>=Captured+25);
    const auto LaterCombat=Later->GetObjectField(TEXT("combat"));
    for (int32 I=0;I<Combat->GetArrayField(TEXT("statuses")).Num();++I)
    {
        const auto First=Combat->GetArrayField(TEXT("statuses"))[I]->AsObject(),Second=LaterCombat->GetArrayField(TEXT("statuses"))[I]->AsObject();
        TestEqual(TEXT("Same-frame CPU time cannot renew a status expiry"),Second->GetNumberField(TEXT("expiresAtUnixMs")),First->GetNumberField(TEXT("expiresAtUnixMs")));
        TestEqual(TEXT("Capture work cannot move periodic cadence"),Second->GetNumberField(TEXT("nextTickAtUnixMs")),First->GetNumberField(TEXT("nextTickAtUnixMs")));
    }
    TestEqual(TEXT("Known GAS expiry is bound to its actual application handle"),LaterCombat->GetArrayField(TEXT("ascEffects"))[0]->AsObject()->GetNumberField(TEXT("expiresAtUnixMs")),Combat->GetArrayField(TEXT("ascEffects"))[0]->AsObject()->GetNumberField(TEXT("expiresAtUnixMs")));
    TestEqual(TEXT("Same-frame UTC work cannot renew global cooldown"),Later->GetObjectField(TEXT("abilities"))->GetNumberField(TEXT("globalCooldownExpiresAtUnixMs")),Saved->GetObjectField(TEXT("abilities"))->GetNumberField(TEXT("globalCooldownExpiresAtUnixMs")));
    TestEqual(TEXT("Same-frame UTC work cannot renew class cooldown"),Later->GetObjectField(TEXT("abilities"))->GetArrayField(TEXT("cooldowns"))[0]->AsObject()->GetNumberField(TEXT("expiresAtUnixMs")),Saved->GetObjectField(TEXT("abilities"))->GetArrayField(TEXT("cooldowns"))[0]->AsObject()->GetNumberField(TEXT("expiresAtUnixMs")));
    const auto DefinitionRow=Combat->GetArrayField(TEXT("definitions"))[0]->AsObject(); FWarAbilityDefinition Decoded;
    TestTrue(TEXT("Recorded immutable condition payload decodes"),WarCampaignCombatDefinition::Decode(DefinitionRow->GetStringField(TEXT("payload")),DefinitionRow->GetStringField(TEXT("sha256")),Decoded,Error));
    TestEqual(TEXT("Applied condition survives current catalog edits"),Decoded.Conditions[0].Actions[0].Value,3.f);
    auto Abilities=Saved->GetObjectField(TEXT("abilities")); Abilities->SetNumberField(TEXT("resource"),5);
    Abilities->SetNumberField(TEXT("globalCooldown"),4); Abilities->SetNumberField(TEXT("globalCooldownExpiresAtUnixMs"),Captured+4000);
    auto ClassCooldown=MakeShared<FJsonObject>(); ClassCooldown->SetStringField(TEXT("id"),TEXT("battle_prelate.custody"));
    ClassCooldown->SetNumberField(TEXT("remaining"),10); ClassCooldown->SetNumberField(TEXT("expiresAtUnixMs"),Captured+10000);
    Abilities->SetArrayField(TEXT("cooldowns"),{MakeShared<FJsonValueObject>(ClassCooldown)});
    Status->Clear(); ASC->RemoveActiveEffects(FGameplayEffectQuery());
    int64 RemovedEpoch=0;TestFalse(TEXT("Actual GAS removal releases its handle custody"),PS->GetCampaignEffectEpoch(OriginalCooldownHandle,RemovedEpoch));
    TestTrue(TEXT("Actual downtime restores effects and epochs"),PS->RestoreCampaignState(Saved,Error,false,Captured+2000));
    auto Recaptured=PS->CaptureCampaignState(Error);
    if (!TestNotNull(TEXT("Restored fixed deadlines remain capturable"),Recaptured.Get())) { AddError(Error);return false; }
    TestEqual(TEXT("Restore preserves the original GAS epoch exactly"),Recaptured->GetObjectField(TEXT("combat"))->GetArrayField(TEXT("ascEffects"))[0]->AsObject()->GetNumberField(TEXT("expiresAtUnixMs")),Combat->GetArrayField(TEXT("ascEffects"))[0]->AsObject()->GetNumberField(TEXT("expiresAtUnixMs")));
    TestEqual(TEXT("Restored GAS state keeps the first actual application epoch"),Recaptured->GetObjectField(TEXT("combat"))->GetArrayField(TEXT("ascEffects"))[0]->AsObject()->GetNumberField(TEXT("expiresAtUnixMs")),double(OriginalCooldownEpoch));
    TestEqual(TEXT("Restore preserves the class cooldown epoch exactly"),Recaptured->GetObjectField(TEXT("abilities"))->GetArrayField(TEXT("cooldowns"))[0]->AsObject()->GetNumberField(TEXT("expiresAtUnixMs")),Captured+10000.);
    TestEqual(TEXT("Offline healing never changes health"),PS->GetAttributes()->GetHealth(),73.f);
    TestEqual(TEXT("Offline ticks never grant receipts"),PS->CaptureScenarioState()->GetArrayField(TEXT("rewards")).Num(),0);
    TestEqual(TEXT("Remaining consumed shield is restored exactly"),Status->GetActive()[0].Shield,ShieldBefore);
    const auto* Periodic=Status->GetActive().FindByPredicate([](const auto& S) { return S.Category==TEXT("hot"); });
    TestTrue(TEXT("Overdue offline ticks are skipped before next cadence"),Periodic && Periodic->NextTick>World->GetTimeSeconds() && Periodic->NextTick<=World->GetTimeSeconds()+.501);
    TestTrue(TEXT("Class cooldown loses elapsed downtime"),FMath::IsNearlyEqual(PS->GetClassAbilities()->Cooldown(TEXT("battle_prelate.custody")),8.f,.01f));
    TestTrue(TEXT("Global cooldown loses elapsed downtime"),FMath::IsNearlyEqual(PS->GetClassAbilities()->Cooldown(TEXT("other")),2.f,.01f));
    const auto RemainingAsc=ASC->GetActiveEffectsTimeRemaining(FGameplayEffectQuery());
    const float ExpectedAscRemaining=FMath::Max(0.,(OriginalCooldownEpoch-Captured-2000)/1000.);
    TestTrue(TEXT("Supported GAS cooldown loses downtime from its actual application epoch"),RemainingAsc.Num()==1 && FMath::IsNearlyEqual(RemainingAsc[0],ExpectedAscRemaining,.002f));
    auto Bad=Copy(Saved); Bad->GetObjectField(TEXT("combat"))->GetArrayField(TEXT("definitions"))[0]->AsObject()->SetStringField(TEXT("sha256"),FString::ChrN(64,TEXT('0')));
    const int32 LiveBefore=Status->GetActive().Num();
    TestFalse(TEXT("Tampered exact applied definition is rejected atomically"),PS->RestoreCampaignState(Bad,Error,false,Captured+2000));
    TestEqual(TEXT("Rejected restore preserves live effects"),Status->GetActive().Num(),LiveBefore);
    Bad=Copy(Saved); Bad->GetObjectField(TEXT("abilities"))->SetNumberField(TEXT("globalCooldownExpiresAtUnixMs"),Captured+9000);
    TestFalse(TEXT("Mismatched relative and epoch cooldown cannot reinterpret time"),PS->RestoreCampaignState(Bad,Error,false,Captured+2000));
    Bad=Copy(Saved); Bad->GetObjectField(TEXT("abilities"))->SetStringField(TEXT("resource"),TEXT("5"));
    TestFalse(TEXT("UE coercion cannot accept a string as a native numeric resource"),PS->RestoreCampaignState(Bad,Error,false,Captured+2000));
    PC->UnPossess(); Pawn->Destroy();
    auto* NewPawn=World->SpawnActor<AWarCharacter>(); NewPawn->SetPlayerState(PS); PC->Possess(NewPawn); ASC->InitAbilityActorInfo(PS,NewPawn); Status=UWarCombatStatus::On(NewPawn);
    TestTrue(TEXT("Same authenticated character rebinds after avatar replacement"),PS->RestoreCampaignState(Saved,Error,false,Captured+2000));
    Recaptured=PS->CaptureCampaignState(Error);
    TestTrue(TEXT("Avatar replacement retains the PlayerState GAS handle deadline"),Recaptured && Recaptured->GetObjectField(TEXT("combat"))->GetArrayField(TEXT("ascEffects"))[0]->AsObject()->GetNumberField(TEXT("expiresAtUnixMs"))==Combat->GetArrayField(TEXT("ascEffects"))[0]->AsObject()->GetNumberField(TEXT("expiresAtUnixMs")));
    TestTrue(TEXT("Source observations refer to the new live identity"),Status->GetActive().ContainsByPredicate([&](const auto& S) { return S.Source==NewPawn && S.SourceCombatant==FName(*NewPawn->GetPathName()); }));
    Status->Apply(Applied->Effects[1],Applied->Id,NewPawn,20,3,Applied->Version,-1,Applied);
    TestEqual(TEXT("Recasting replaces the restored same-source effect"),Status->GetActive().Num(),4);
    for (auto& S:Status->Active) if (S.Category==TEXT("hot") || S.Category==TEXT("dot"))
    { S.NextTick=World->GetTimeSeconds()-6;S.NextTickUnixMs=WarCampaignCombatState::UnixMs()-6000; }
    PS->SetScenarioTransferPending(true); Status->TickComponent(.05f,LEVELTICK_All,nullptr);
    TestEqual(TEXT("A durable transfer hold does not apply periodic healing"),PS->GetAttributes()->GetHealth(),73.f);
    TestTrue(TEXT("Held periodic ticks skip backlog before a custody ACK"),Status->GetActive().ContainsByPredicate([&](const auto& S) { return S.Category==TEXT("hot") && S.NextTick>World->GetTimeSeconds(); }));
    PS->SetScenarioTransferPending(false);
    Bad=Copy(Saved); for (const auto& Value:Bad->GetObjectField(TEXT("combat"))->GetArrayField(TEXT("statuses")))
    {
        auto Row=Value->AsObject(); const FString Previous=Row->GetStringField(TEXT("sourceKey")); const FString Missing=TEXT("human:missing-authenticated-source");
        Row->SetStringField(TEXT("sourceKey"),Missing); Row->SetStringField(TEXT("id"),Row->GetStringField(TEXT("id")).Replace(*Previous,*Missing));
    }
    TestFalse(TEXT("An unexpired missing live source keeps recovery protected"),PS->RestoreCampaignState(Bad,Error,false,Captured+2000));
    auto* ReplacementBot=World->SpawnActor<AWarSiegeBotController>();
    ReplacementBot->CampaignCombatSourceKey=TEXT("encounter:recorded:0:aegis:guard:1:22222222222222222222222222222222");
    auto* BotState=World->SpawnActor<AWarPlayerState>(); ReplacementBot->PlayerState=BotState; BotState->SetOwner(ReplacementBot); BotState->SetDevelopmentRealm(EWarRealm::Aegis);
    auto* ReplacementGuard=World->SpawnActor<AWarCharacter>(); ReplacementGuard->SetPlayerState(BotState); ReplacementBot->Possess(ReplacementGuard);
    auto OldBirth=Copy(Saved);
    for (const auto& Value:OldBirth->GetObjectField(TEXT("combat"))->GetArrayField(TEXT("statuses")))
    {
        auto Row=Value->AsObject(); const FString Previous=Row->GetStringField(TEXT("sourceKey"));
        const FString OriginalBirth=TEXT("encounter:recorded:0:aegis:guard:1:11111111111111111111111111111111");
        Row->SetStringField(TEXT("sourceKey"),OriginalBirth); Row->SetStringField(TEXT("id"),Row->GetStringField(TEXT("id")).Replace(*Previous,*OriginalBirth));
    }
    TestFalse(TEXT("A new same-role NPC birth never substitutes for the recorded source"),PS->RestoreCampaignState(OldBirth,Error,false,Captured+2000));
    TestTrue(TEXT("A stable NPC identity resolves only its actual birth"),WarCampaignCombatState::Resolve(World,ReplacementBot->CampaignCombatSourceKey)==ReplacementGuard);
    TestTrue(TEXT("Missing live source may expire naturally without retargeting"),PS->RestoreCampaignState(Bad,Error,false,Captured+31000));
    TestEqual(TEXT("Expired effects are never rescheduled"),Status->GetActive().Num(),0);
    TestTrue(TEXT("Valid recorded effects restore again for rollback proof"),PS->RestoreCampaignState(Saved,Error,false,Captured+2000));
    auto* Bridge=World->GetSubsystem<UWarCampaignSiegeSubsystem>(); Bridge->bBusy=true;
    Bridge->Url=TEXT("http://127.0.0.1"); Bridge->Token=TEXT("unused-local-test-token");
    auto* Siege=World->SpawnActor<AWarSiegeEncounter>(); Siege->bCampaign=true; Siege->ActivationId=TEXT("actual-test-custody"); PS->SetSiegeMembership(Siege);
    const int32 Revision=PS->GetInventory().Revision; const FGuid Receipt=FGuid::NewGuid();
    TestFalse(TEXT("Rejected critical WAL mutation still reports failure"),PS->GrantCharacterRewards(Receipt,25,5,{},Error));
    TestEqual(TEXT("Critical rollback preserves normal inventory"),PS->GetInventory().Revision,Revision);
    TestEqual(TEXT("Critical rollback preserves exact live effects"),Status->GetActive().Num(),4);
    TestEqual(TEXT("Critical rollback preserves consumed shield"),Status->GetActive()[0].Shield,ShieldBefore);
    auto* Opaque=NewObject<UGameplayEffect>(World); Opaque->DurationPolicy=EGameplayEffectDurationType::Infinite;
    FGameplayEffectSpec OpaqueSpec(Opaque,ASC->MakeEffectContext(),1); const auto OpaqueHandle=ASC->ApplyGameplayEffectSpecToSelf(OpaqueSpec);
    TestNull(TEXT("Opaque effects cannot silently disappear from a complete snapshot"),PS->CaptureCampaignState(Error).Get());
    TestFalse(TEXT("Unknown effects reject a critical mutation before inventory changes"),PS->GrantCharacterRewards(FGuid::NewGuid(),25,5,{},Error));
    TestEqual(TEXT("Unsupported snapshot preserves inventory revision"),PS->GetInventory().Revision,Revision);
    TestNotNull(TEXT("Unsupported native effect remains active"),ASC->GetActiveGameplayEffect(OpaqueHandle));
    TestFalse(TEXT("Restore does not wipe an opaque existing effect"),PS->RestoreCampaignState(Saved,Error,false,Captured+2000));
    ASC->RemoveActiveGameplayEffect(OpaqueHandle); PS->SetSiegeMembership(nullptr);
    TestTrue(TEXT("Defeated respawn restores cooldowns while clearing pawn statuses"),PS->RestoreCampaignState(Saved,Error,true,Captured+2000));
    TestEqual(TEXT("Respawn clears pawn-local effects"),Status->GetActive().Num(),0); TestEqual(TEXT("Respawn retains normal max health"),PS->GetAttributes()->GetHealth(),100.f);
    auto Historical=PS->CaptureScenarioState(); Historical->GetObjectField(TEXT("abilities"))->SetNumberField(TEXT("globalCooldown"),4);
    TestTrue(TEXT("Historical missing-version snapshot keeps recorded relative timer semantics"),PS->RestoreCampaignState(Historical,Error,false,Captured+60000));
    TestTrue(TEXT("Legacy relative global cooldown remains four seconds"),FMath::IsNearlyEqual(PS->GetClassAbilities()->Cooldown(TEXT("other")),4.f,.01f));
    Historical->SetObjectField(TEXT("combat"),Combat);
    TestFalse(TEXT("Partial v2 cannot fall back to historical omitted effects"),PS->RestoreCampaignState(Historical,Error));
    Status->Clear();
    auto Fractional=MakeShared<FWarAbilityDefinition>(*Applied);Fractional->Conditions.Reset();Fractional->Effects[2].Interval=.3333f;
    Status->ApplyPeriodic(Fractional->Effects[2],0,NewPawn,NewPawn,Fractional,20,3,false);
    if (!TestEqual(TEXT("Fractional cadence fixture has one authentic periodic status"),Status->Active.Num(),1)) return false;
    const double CadenceOrigin=Status->Active[0].NextTickUnixMs;
    const double CadenceStep=double(Status->Active[0].Interval)*1000.;
    // Dispatch the real tick branch at a fixed test world time; the epoch cache must not truncate each fractional step.
    for (int32 I=0;I<30;++I)
    { Status->Active[0].NextTick=World->GetTimeSeconds()-.001;Status->TickComponent(.3333f,LEVELTICK_All,nullptr); }
    const double ExpectedCadence=CadenceOrigin+30*CadenceStep;
    TestTrue(TEXT("Repeated fractional native intervals retain their unrounded epoch cadence"),FMath::Abs(Status->Active[0].NextTickUnixMs-ExpectedCadence)<.01);
    TSharedPtr<FJsonObject> FractionalState;
    TestTrue(TEXT("Fractional cadence remains a complete supported capture"),Status->CaptureCampaignState(WarCampaignCombatState::UnixMs(),FractionalState,Error));
    if (FractionalState)
        TestEqual(TEXT("Only the final serialized cadence rounds to integer milliseconds"),FractionalState->GetArrayField(TEXT("statuses"))[0]->AsObject()->GetNumberField(TEXT("nextTickAtUnixMs")),double(FMath::RoundToInt64(ExpectedCadence)));
    return !HasAnyErrors();
}
#endif
