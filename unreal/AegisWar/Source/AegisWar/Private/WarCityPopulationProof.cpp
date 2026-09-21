#include "WarCityPopulationProof.h"
#include "WarCityNpc.h"
#include "WarCityServices.h"
#include "WarQuestNpc.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarContentSubsystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "TimerManager.h"
#include "UnrealClient.h"

bool UWarCityPopulationProof::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(),TEXT("WarCityPopulationProof"))
        && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentGM"));
#endif
}
TStatId UWarCityPopulationProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarCityPopulationProof,STATGROUP_Tickables); }
void UWarCityPopulationProof::Finish(bool Passed,const FString& Detail)
{
    bFinished=true;
    const FString Folder=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("CityPopulationProof"));
    IFileManager::Get().MakeDirectory(*Folder,true);
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Passed);Report->SetStringField(TEXT("detail"),Detail);
    Report->SetStringField(TEXT("map"),GetWorld()->GetOutermost()->GetName());
    Report->SetBoolField(TEXT("durableEconomyAcceptance"),false);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*FPaths::Combine(Folder,TEXT("report.json")));
    const bool Capture=Passed && FParse::Param(FCommandLine::Get(),TEXT("WarProofScreenshot"));
    if (Capture)
    {
        FTimerHandle Timer;
        GetWorld()->GetTimerManager().SetTimer(Timer,[Folder]{FScreenshotRequest::RequestScreenshot(FPaths::Combine(Folder,TEXT("merchant.png")),true,false);},3.f,false);
    }
    FTimerHandle Exit;
    GetWorld()->GetTimerManager().SetTimer(Exit,[Passed]{FPlatformMisc::RequestExitWithStatus(false,Passed?0:1);},Capture?5.f:1.f,false);
}
void UWarCityPopulationProof::Tick(float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now=GetWorld()->GetTimeSeconds();if (Started<0) Started=Now;
    if (!bLoaded)
    {
        UGameplayStatics::LoadStreamLevel(GetWorld(),TEXT("/Game/Capitals/crownward/Population/AegisCapital_Population"),true,true,FLatentActionInfo());
        bLoaded=true;return;
    }
    auto* Controller=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Pawn=Controller?Cast<AWarCharacter>(Controller->GetPawn()):nullptr;
    auto* State=Controller?Controller->GetPlayerState<AWarPlayerState>():nullptr;
    if (!Pawn || !State || !Pawn->IsVisualReady())
    { if (Now-Started>45) Finish(false,TEXT("Player failed to initialize"));return; }
    const auto Check=[this](bool Good,const FString& Message){if(!Good)Finish(false,Message);return Good;};
    if (AnimationSampleTime < 0)
    {
        for (TActorIterator<AWarCityNpc> It(GetWorld());It;++It)
            if (const auto* Idle=It->GetSkeletalMeshComponent()->GetSingleNodeInstance())
                AnimationSamples.Add(It->NpcId,Idle->GetCurrentTime());
        AnimationSampleTime=Now;
        return;
    }
    if (Now-AnimationSampleTime < .5) return;
    TSet<FName> Ids;TArray<AWarCityNpc*> Merchants;int32 Teachers=0;
    for (TActorIterator<AWarCityNpc> It(GetWorld());It;++It)
    {
        auto* Mesh=It->GetSkeletalMeshComponent();
        if (!Check(!Ids.Contains(It->NpcId) && !It->NpcId.IsNone() && Mesh && Mesh->GetSkeletalMeshAsset()
            && Mesh->AnimationData.AnimToPlay && Mesh->AnimationData.bSavedLooping && Mesh->AnimationData.bSavedPlaying,
            TEXT("Missing/duplicate NPC identity, complex mesh or saved idle animation"))) return;
        Ids.Add(It->NpcId);
        const auto* Idle=Mesh->GetSingleNodeInstance();
        const float* Earlier=AnimationSamples.Find(It->NpcId);
        if (!Check(Idle && Earlier && !FMath::IsNearlyEqual(*Earlier,Idle->GetCurrentTime()),
            TEXT("Idle animation did not advance: ")+It->NpcId.ToString())) return;
        for (const auto* Material:Mesh->GetMaterials())
            if (!Check(Material!=nullptr,TEXT("NPC material missing: ")+It->NpcId.ToString())) return;
        const FVector P=It->GetActorLocation();FHitResult Ground;
        if (!Check(GetWorld()->LineTraceSingleByChannel(Ground,P+FVector(0,0,100),P-FVector(0,0,35),ECC_Visibility)
            && Ground.ImpactNormal.Z>.65,TEXT("NPC has no nearby walkable ground: ")+It->NpcId.ToString())) return;
        if (!WarCityServices::Offers(It->GetService()).IsEmpty()) Merchants.Add(*It);
        if (It->GetService()==TEXT("class_teacher") || It->GetService()==TEXT("craft_teacher")) ++Teachers;
    }
    int32 Mara=0;for(TActorIterator<AWarQuestNpc> It(GetWorld());It;++It) if(It->NpcId==TEXT("quest-1"))++Mara;
    if (!Check(Ids.Num()==17 && Mara==1 && Merchants.Num()==2 && Teachers==2,TEXT("Expected 17 new people, Mara once, two merchants and two teachers")))return;
    FString Error;
    if (!Check(State->GrantCharacterRewards(FGuid::NewGuid(),0,500,{},Error),Error))return;
    for(auto* Merchant:Merchants)
    {
        if (!Check(Pawn->TeleportTo(Merchant->GetActorLocation()+FVector(200,0,110),FRotator::ZeroRotator),TEXT("Merchant approach is obstructed"))) return;
        const auto Offers=WarCityServices::Offers(Merchant->GetService());
        for(const auto& Offer:Offers)
        {
            const FGuid Transaction=FGuid::NewGuid();const auto Before=State->GetInventory();
            if(!Check(State->TradeWithCityNpc(Merchant,Transaction,Offer.Key,false,1,INDEX_NONE,Before.Revision,Error),Error))return;
            if(!Check(State->GetInventory().CharacterProgression.Gold==Before.CharacterProgression.Gold-Offer.Value,TEXT("Buy gold delta wrong")))return;
            if(!Check(!State->TradeWithCityNpc(Merchant,Transaction,Offer.Key,false,1,INDEX_NONE,State->GetInventory().Revision,Error),TEXT("Duplicate purchase accepted")))return;
            if(!Check(!State->TradeWithCityNpc(Merchant,FGuid::NewGuid(),Offer.Key,false,1,INDEX_NONE,Before.Revision,Error),TEXT("Stale purchase accepted")))return;
            const auto* Item=State->GetInventory().Items.FindByPredicate([&Offer](const auto& Row){return Row.Key==Offer.Key;});
            if(!Check(Item!=nullptr,TEXT("Bought item missing")))return;
            if(!Check(State->TradeWithCityNpc(Merchant,FGuid::NewGuid(),Offer.Key,true,1,Item->Slot,State->GetInventory().Revision,Error),Error))return;
        }
        const auto Before=State->GetInventory();
        if(!Check(!State->TradeWithCityNpc(Merchant,FGuid::NewGuid(),TEXT("fake_item"),false,1,INDEX_NONE,Before.Revision,Error),TEXT("Unknown goods accepted")))return;
        Merchant->SetActorHiddenInGame(true);
        if(!Check(!State->TradeWithCityNpc(Merchant,FGuid::NewGuid(),Offers.CreateConstIterator().Key(),false,1,INDEX_NONE,Before.Revision,Error),TEXT("Hidden merchant accepted")))return;
        Merchant->SetActorHiddenInGame(false);
        Pawn->SetActorLocation(Merchant->GetActorLocation()+FVector(1500,0,110),false,nullptr,ETeleportType::TeleportPhysics);
        if(!Check(!State->TradeWithCityNpc(Merchant,FGuid::NewGuid(),Offers.CreateConstIterator().Key(),false,1,INDEX_NONE,Before.Revision,Error),TEXT("Distant merchant accepted")))return;
        if(!Check(State->GetInventory().Revision==Before.Revision,TEXT("Rejected trades mutated inventory")))return;
    }
    const auto* Content=GetWorld()->GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
    const auto Classes=Content->GetCityTeachingText(TEXT("class_teacher"));
    const auto Crafts=Content->GetCityTeachingText(TEXT("craft_teacher"));
    if(!Check(Classes.Contains(TEXT("Spark Lash")) && Classes.Contains(TEXT("Heat")) && Classes.Contains(TEXT("Level 1"))
        && Crafts.Contains(TEXT("Scavenging")) && Crafts.Contains(TEXT("station:")),TEXT("Teaching catalog guidance missing")))return;
    auto* Merchant=Merchants[0];Pawn->TeleportTo(Merchant->GetActorLocation()+FVector(200,0,110),FRotator::ZeroRotator);
    Controller->OpenCityService(Merchant);
    Finish(true,TEXT("18 identities, advancing idle playback, assigned materials, grounded placements, six buy/sell pairs, duplicate/stale/distance/hidden/catalog rejection and teacher catalog guidance passed."));
}
