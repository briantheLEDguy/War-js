#include "WarCombatNetworkProof.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAbilityRuntime.h"
#include "WarAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "AIController.h"
#include "Components/BoxComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

bool UWarCombatNetworkProof::ShouldCreateSubsystem(UObject* Outer) const
{
    return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer)
        && FParse::Param(FCommandLine::Get(),TEXT("WarCombatNetworkProof"))
        && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentNetworking"));
}
bool UWarCombatNetworkProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type==EWorldType::Game; }
TStatId UWarCombatNetworkProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarCombatNetworkProof,STATGROUP_Tickables); }
void UWarCombatNetworkProof::Finish(bool bPassed,const FString& Detail)
{
    bFinished=true; FString Run; FParse::Value(FCommandLine::Get(),TEXT("WarProofRun="),Run);
    const FString Directory=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("CombatNetworkProof"),Run);
    IFileManager::Get().MakeDirectory(*Directory,true);
    auto Report=MakeShared<FJsonObject>(); Report->SetBoolField(TEXT("passed"),bPassed); Report->SetStringField(TEXT("detail"),Detail);
    Report->SetBoolField(TEXT("predictedMovement"),bPredictedMovement);
    FString Json; FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*FPaths::Combine(Directory,GetWorld()->GetNetMode()==NM_Client ? TEXT("client.json") : TEXT("server.json")));
}
void UWarCombatNetworkProof::Tick(float Delta)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now=GetWorld()->GetTimeSeconds(); if (Started<0) Started=Now;
    if (Now-Started>120) { Finish(false,TEXT("Timed out waiting for owner cast, movement cancellation and replicated refund")); return; }
    auto* Catalog=GetWorld()->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>();
    if (GetWorld()->GetNetMode()==NM_DedicatedServer)
    {
        if (!Actor.IsValid())
        {
            AWarPlayerController* PC=nullptr;
            for (TActorIterator<AWarPlayerController> It(GetWorld());It;++It) if (It->GetNetConnection()) { PC=*It; break; }
            if (!PC || !PC->GetPlayerState<AWarPlayerState>()) return;
            auto* Floor=GetWorld()->SpawnActor<AActor>(); auto* Shape=NewObject<UBoxComponent>(Floor);
            Floor->SetRootComponent(Shape); Floor->SetReplicates(true); Floor->bAlwaysRelevant=true;
            Shape->SetBoxExtent(FVector(3000,3000,20)); Shape->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
            Shape->SetCollisionResponseToAllChannels(ECR_Block); Shape->SetIsReplicated(true); Shape->RegisterComponent(); Floor->SetActorLocation(FVector(0,0,2980));
            const auto Spawn=[&](const TCHAR* Profile,FVector Position,AController* Controller) {
                auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,*(FString(TEXT("/Game/MigrationProof/Visual_"))+Profile));
                if (!Visual) return static_cast<AWarCharacter*>(nullptr);
                FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
                auto* Pawn=GetWorld()->SpawnActor<AWarCharacter>(Position,FRotator::ZeroRotator,Params); Controller->Possess(Pawn);
                auto* State=Controller->GetPlayerState<AWarPlayerState>();
                if (!State) { State=GetWorld()->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State); }
                State->SetDevelopmentRealm(Visual->Realm); State->SetCurrentZoneTrusted(TEXT("aegis_capital")); FString Error;
                if (!Pawn->SetVisualDefinition(Visual,Error)) { Finish(false,Error); return static_cast<AWarCharacter*>(nullptr); }
                State->InitializeForPawn(Pawn); State->SetSiegeNormalized(true); State->GetClassAbilities()->InitializeCharacter(Pawn);
                State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),2000);
                State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),2000);
                State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),100);
                Pawn->bAlwaysRelevant=true; Pawn->ForceNetUpdate(); return Pawn;
            };
            if (APawn* Old=PC->GetPawn()) { PC->UnPossess(); Old->Destroy(); }
            Actor=Spawn(TEXT("civic_ember_arcanist_m"),FVector(0,0,3099),PC);
            Target=Spawn(TEXT("mire_warbrute_m"),FVector(500,0,3099),GetWorld()->SpawnActor<AAIController>());
            if (!Actor.IsValid() || !Target.IsValid()) { Finish(false,TEXT("Missing imported network fixtures")); return; }
            auto Definitions=Catalog->All();
            const auto Kit=Catalog->Kit(Actor->GetCareerId()); if (Kit.IsEmpty()) { Finish(false,TEXT("Missing caster kit")); return; }
            Ability=Kit[0]->Id;
            for (auto& A:Definitions) if (A.Id==Ability)
            {
                A.bAuthoredTiming=true; A.TimingMode=TEXT("cast"); A.CastSeconds=1.5f; A.bCancelOnMovement=true;
                A.Cooldown=4; A.Gcd=1; A.Mana=10; A.Cost=20; A.Build=5; A.ResourceMax=100; A.MinimumResource=0; A.UnlockLevel=1;
            }
            FString Error; if (!Catalog->Install(Definitions,TEXT("baseline"),Error)) { Finish(false,Error); return; }
            Actor->GetPlayerState<AWarPlayerState>()->GetClassAbilities()->RestoreResource(); return;
        }
        auto* State=Actor->GetPlayerState<AWarPlayerState>(); auto* Runtime=State->GetClassAbilities();
        if (Phase==0 && !Runtime->GetCastingAbility().IsNone()) { ActionAt=Now; Phase=1; }
        if (Phase==1 && Now-ActionAt>2)
        {
            const bool Passed=Runtime->GetCastingAbility().IsNone() && State->GetAttributes()->GetMana()==100
                && Runtime->GetResource()==100 && Runtime->Cooldown(Ability)==0 && Actor->GetActorLocation().Y>5
                && Target->GetPlayerState<AWarPlayerState>()->GetAttributes()->GetHealth()==2000;
            Finish(Passed,TEXT("Authority checks: movement, cancelled cast, isolated refund, retained/expired GCD and no delayed hit"));
        }
        return;
    }
    if (GetWorld()->GetNetMode()!=NM_Client) return;
    auto* PC=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Pawn=PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    auto* State=Pawn ? Pawn->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!State || !Pawn->IsVisualReady() || Pawn->GetAnimationProfile()!=TEXT("civic_ember_arcanist_m")) return;
    auto* Runtime=State->GetClassAbilities();
    if (Phase==0 && Now-Started>8)
    {
        AWarCharacter* Enemy=nullptr;
        for (TActorIterator<AWarCharacter> It(GetWorld());It;++It) if (It->GetAnimationProfile()==TEXT("mire_warbrute_m")) { Enemy=*It; break; }
        const auto Kit=Catalog->Kit(Pawn->GetCareerId()); if (!Enemy || Kit.IsEmpty()) return;
        Runtime->ServerActivateVersioned(Kit[0]->Id,Enemy,Catalog->GetVersion(),FVector::ZeroVector); Phase=1;
    }
    if (Phase==1 && !Runtime->GetCastingAbility().IsNone())
    { MovementAt=Now; MovementOrigin=Pawn->GetActorLocation(); Runtime->UpdateMovementIntent(true); Phase=2; }
    if (Phase==2)
    {
        Pawn->AddMovementInput(FVector(0,1,0),1);
        if (Now-MovementAt>.08 && Now-MovementAt<.15) bPredictedMovement|=Pawn->GetActorLocation().Y-MovementOrigin.Y>1;
        if (Now-MovementAt>.35) { Runtime->UpdateMovementIntent(false); Phase=3; }
    }
    if (Phase==3 && Now-MovementAt>1.2)
        Finish(bPredictedMovement && Runtime->GetCastingAbility().IsNone() && State->GetAttributes()->GetMana()==100 && Runtime->GetResource()==100,
            TEXT("Owner checks: predicted movement within 150ms, authoritative cancellation and replicated resource refund"));
}
