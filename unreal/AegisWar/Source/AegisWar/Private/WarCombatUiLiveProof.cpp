#include "WarCombatUiLiveProof.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarCombatFeedback.h"
#include "WarOverheadHealth.h"
#include "AbilitySystemComponent.h"
#include "AIController.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

namespace
{
    const TCHAR* Names[] = {TEXT("UI Owner"), TEXT("Enemy player"), TEXT("Friendly player"), TEXT("Enemy NPC"), TEXT("Friendly NPC")};
    const TCHAR* Profiles[] = {TEXT("civic_ember_arcanist_m"), TEXT("mire_warbrute_m"), TEXT("civic_battle_prelate_m"), TEXT("mire_warbrute_m"), TEXT("civic_battle_prelate_m")};
    const FVector Positions[] = {FVector(-600,0,3000), FVector(400,260,3000), FVector(400,-260,3000), FVector(850,350,3000), FVector(850,-350,3000)};
    bool Enemy(int32 Index) { return Index==1 || Index==3; }
}

bool UWarCombatUiLiveProof::ShouldCreateSubsystem(UObject* Outer) const
{
    return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer)
        && FParse::Param(FCommandLine::Get(),TEXT("WarCombatUiLiveProof"))
        && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentNetworking"));
}
bool UWarCombatUiLiveProof::DoesSupportWorldType(EWorldType::Type Type) const { return Type==EWorldType::Game; }
TStatId UWarCombatUiLiveProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarCombatUiLiveProof,STATGROUP_Tickables); }
FString UWarCombatUiLiveProof::Directory() const
{
    FString Run; FGuid Id;
    if (!FParse::Value(FCommandLine::Get(),TEXT("WarUiLiveRun="),Run) || !FGuid::Parse(Run,Id)) return FString();
    return FPaths::ProjectSavedDir()/TEXT("CombatUiLiveProof")/Id.ToString(EGuidFormats::Digits);
}
void UWarCombatUiLiveProof::Finish(bool Passed,const FString& Detail)
{
    Finished=true;
    const FString Folder=Directory(); if (Folder.IsEmpty()) return;
    IFileManager::Get().MakeDirectory(*Folder,true);
    auto Report=MakeShared<FJsonObject>();
    Report->SetBoolField(TEXT("passed"),Passed);
    Report->SetStringField(TEXT("detail"),Detail);
    Report->SetNumberField(TEXT("observedRecipientMask"),Observed);
    Report->SetNumberField(TEXT("movedRecipientMask"),Moved);
    Report->SetArrayField(TEXT("captures"),Captures);
    FString Json; FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(Folder/(GetWorld()->GetNetMode()==NM_DedicatedServer?TEXT("server.json"):TEXT("owner.json"))));
}
void UWarCombatUiLiveProof::Tick(float Delta)
{
    if (Finished || !GetWorld()->HasBegunPlay() || Directory().IsEmpty()) return;
    const double Now=GetWorld()->GetTimeSeconds(); if (Started<0) Started=Now;
    if (Now-Started>150) { Finish(false,FString::Printf(TEXT("Live UI proof timed out: captures %d, recipient mask %d"),CaptureIndex,Observed)); return; }
    if (GetWorld()->GetNetMode()==NM_DedicatedServer)
    {
        if (Actors.IsEmpty())
        {
            TArray<AWarPlayerController*> Players;
            for (TActorIterator<AWarPlayerController> It(GetWorld());It;++It)
                if (It->GetNetConnection() && It->GetPlayerState<AWarPlayerState>()) Players.Add(*It);
            if (Players.Num()!=3) return;
            // The runner awaits each completed join before starting the next client.
            // LocalPlayer overrides URL names, so server creation order assigns fixture roles.
            Players.Sort([](const AWarPlayerController& A,const AWarPlayerController& B) { return A.GetUniqueID()<B.GetUniqueID(); });
            for (int32 I=0;I<5;++I)
            {
                AController* Controller=I<3?static_cast<AController*>(Players[I]):GetWorld()->SpawnActor<AAIController>();
                auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,*(FString(TEXT("/Game/MigrationProof/Visual_"))+Profiles[I]));
                if (!Visual || !Controller) { Finish(false,TEXT("Missing imported live UI fixture")); return; }
                if (APawn* Old=Controller->GetPawn()) { Controller->UnPossess(); Old->Destroy(); }
                FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
                auto* Character=GetWorld()->SpawnActor<AWarCharacter>(Positions[I],FRotator(0,-90,0),Params);
                Controller->Possess(Character);
                auto* State=Controller->GetPlayerState<AWarPlayerState>();
                if (!State) { State=GetWorld()->SpawnActor<AWarPlayerState>(); Character->SetPlayerState(State); }
                State->SetDevelopmentRealm(Visual->Realm); State->SetCurrentZoneTrusted(TEXT("aegis_capital")); State->SetPlayerName(Names[I]);
                FString Error; if (!Character->SetVisualDefinition(Visual,Error)) { Finish(false,Error); return; }
                State->InitializeForPawn(Character); Character->GetCharacterMovement()->DisableMovement();
                State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetMaxHealthAttribute(),1000);
                State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),700);
                Character->bAlwaysRelevant=true; Character->ForceNetUpdate(); Actors.Add(Character);
            }
            ReadyAt=Now; NextFeedback=Now+12; return;
        }
        for (int32 I=1;I<Actors.Num();++I)
        {
            if (!Actors[I].IsValid()) { Finish(false,TEXT("A live recipient disappeared")); return; }
            Actors[I]->SetActorLocation(Positions[I]+FVector(FMath::Sin((Now-ReadyAt)*.8+I)*90,0,0));
            Actors[I]->ForceNetUpdate();
        }
        if (Now>=NextFeedback)
        {
            NextFeedback=Now+.35;
            for (int32 I=1;I<Actors.Num();++I)
            {
                auto* State=Actors[I]->GetPlayerState<AWarPlayerState>();
                State->GetAbilitySystemComponent()->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),500+FMath::RoundToInt(120*FMath::Sin(Now-ReadyAt)));
                WarCombatFeedback::Emit(Actors[0].Get(),Actors[I].Get(),Enemy(I)?TEXT("Hit"):TEXT("Heal"),I*11);
            }
        }
        if (Now-ReadyAt>45) Finish(true,TEXT("Three actual player connections and two NPCs moved with authoritative health and feedback"));
        return;
    }
    if (GetWorld()->GetNetMode()!=NM_Client || !FParse::Param(FCommandLine::Get(),TEXT("WarUiRenderOwner"))) return;
    auto* PC=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    if (!PC || !PC->GetPawn() || !PC->GetPlayerState<AWarPlayerState>()) return;
    TArray<AWarCharacter*> Recipients;
    for (int32 I=1;I<5;++I)
    {
        AWarCharacter* Found=nullptr;
        for (TActorIterator<AWarCharacter> It(GetWorld());It;++It)
            if (It->IsVisualReady() && It->GetPlayerState<AWarPlayerState>() && It->GetPlayerState<AWarPlayerState>()->GetPlayerName()==Names[I]) Found=*It;
        if (!Found) return;
        Recipients.Add(Found);
    }
    if (!Camera.IsValid())
    {
        PC->CloseAllPanels(); PC->ResetCombatUi();
        const FVector Location(0,-2200,3650), Focus(540,0,2900);
        Camera=GetWorld()->SpawnActor<ACameraActor>(Location,(Focus-Location).Rotation());
        Camera->GetCameraComponent()->FieldOfView=55;
        PC->SetViewTarget(Camera.Get());
        IFileManager::Get().MakeDirectory(*Directory(),true);
        for (auto* Recipient:Recipients) FirstPositions.Add(Recipient->GetPlayerState<AWarPlayerState>()->GetPlayerName(),Recipient->GetActorLocation());
    }
    PC->SetViewTarget(Camera.Get());
    for (int32 I=0;I<Recipients.Num();++I)
        if (FVector::Dist(FirstPositions[Recipients[I]->GetPlayerState<AWarPlayerState>()->GetPlayerName()],Recipients[I]->GetActorLocation())>10) Moved|=1<<I;
    for (const auto& N:PC->GetFloatingCombatNumbers())
        for (int32 I=0;I<Recipients.Num();++I)
            if (N.Recipient==Recipients[I] && N.Amount==(I+1)*11 && N.bEnemy==Enemy(I+1)) Observed|=1<<I;
    if (Observed!=15 || Moved!=15) return;
    if (ReadyAt<0) ReadyAt=Now;
    if (CaptureIndex>=4)
    {
        if (Now-ReadyAt>=11) Finish(true,TEXT("Rendered moving remote players/NPCs, recipient-bound numbers, replicated bars and live target switching"));
        return;
    }
    if (Now-ReadyAt<CaptureIndex*2.5+1) return;
    auto* Target=Recipients[CaptureIndex];
    if (!PC->SelectCombatTarget(Target) || PC->GetCombatTarget()!=Target || PC->IsEnemyCombatTarget(Target)!=Enemy(CaptureIndex+1))
    { Finish(false,TEXT("Live target selection or relationship failed")); return; }
    auto Capture=MakeShared<FJsonObject>(); Capture->SetStringField(TEXT("selected"),Names[CaptureIndex+1]);
    int32 ViewWidth=0,ViewHeight=0; PC->GetViewportSize(ViewWidth,ViewHeight);
    TArray<TSharedPtr<FJsonValue>> PositionsJson;
    for (int32 I=0;I<Recipients.Num();++I)
    {
        auto* Recipient=Recipients[I]; FWarOverheadHealth Health; FVector2D Head;
        const auto* State=Recipient->GetPlayerState<AWarPlayerState>();
        const FVector Anchor=WarFloatingCombatText::HeadAnchor(Recipient);
        if (!WarOverheadHealth::Read(PC,Recipient,Health) || Health.bEnemy!=Enemy(I+1)
            || !FMath::IsNearlyEqual(Health.Fraction,State->GetAttributes()->GetHealth()/1000))
        { Finish(false,FString::Printf(TEXT("Recipient health/relationship failed: %s, %.4f, %.0f/%.0f"),*State->GetPlayerName(),Health.Fraction,State->GetAttributes()->GetHealth(),State->GetAttributes()->GetMaxHealth())); return; }
        // Recipients may briefly occlude each other while moving; capture a visible frame.
        if (!PC->LineOfSightTo(Recipient) || !PC->ProjectWorldLocationToScreen(Anchor,Head,true)
            || Head.X<0 || Head.Y<0 || Head.X>=ViewWidth || Head.Y>=ViewHeight) return;
        bool NumberFound=false;
        for (const auto& N:PC->GetFloatingCombatNumbers()) if (N.Recipient==Recipient)
        {
            if (FVector::Dist(N.Anchor,Anchor)>30) { Finish(false,TEXT("Floating number detached from moving recipient")); return; }
            NumberFound=true;
        }
        if (!NumberFound) return; // Wait for the next packet; do not manufacture local feedback.
        auto P=MakeShared<FJsonObject>(); P->SetStringField(TEXT("recipient"),State->GetPlayerName());
        P->SetNumberField(TEXT("headX"),Head.X); P->SetNumberField(TEXT("headY"),Head.Y);
        P->SetNumberField(TEXT("health"),State->GetAttributes()->GetHealth());
        P->SetStringField(TEXT("worldPosition"),Recipient->GetActorLocation().ToString());
        PositionsJson.Add(MakeShared<FJsonValueObject>(P));
    }
    Capture->SetArrayField(TEXT("recipients"),PositionsJson); Captures.Add(MakeShared<FJsonValueObject>(Capture));
    FScreenshotRequest::RequestScreenshot(Directory()/FString::Printf(TEXT("target-%d.png"),CaptureIndex),true,false);
    ++CaptureIndex;
}
