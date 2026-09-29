#include "WarImportedPopulationProof.h"
#include "WarCityNpc.h"
#include "WarEnemy.h"
#include "WarCharacter.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarZoneStreamingSubsystem.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

bool UWarImportedPopulationProof::ShouldCreateSubsystem(UObject* Outer) const
{
    return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer)
        && FParse::Param(FCommandLine::Get(),TEXT("WarDevelopmentGM"))
        && FParse::Param(FCommandLine::Get(),TEXT("WarImportedPopulationProof"));
}
TStatId UWarImportedPopulationProof::GetStatId() const
{ RETURN_QUICK_DECLARE_CYCLE_STAT(UWarImportedPopulationProof,STATGROUP_Tickables); }
void UWarImportedPopulationProof::Finish(bool Passed,const FString& Detail)
{
    bFinished=true;
    const FString Folder=FPaths::ProjectSavedDir()/TEXT("ImportedPopulationProof");
    IFileManager::Get().MakeDirectory(*Folder,true);
    auto Report=MakeShared<FJsonObject>(); Report->SetBoolField(TEXT("passed"),Passed);
    Report->SetStringField(TEXT("detail"),Detail); Report->SetNumberField(TEXT("checked"),Checked);
    Report->SetBoolField(TEXT("productionAccepted"),false);
    FString Json; FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(Folder/TEXT("report.json")));
    UE_LOG(LogTemp,Display,TEXT("WAR_IMPORTED_POPULATION_PROOF passed=%d checked=%d %s"),Passed,Checked,*Detail);
    FPlatformMisc::RequestExitWithStatus(false,Passed?0:1);
}
void UWarImportedPopulationProof::Tick(float DeltaSeconds)
{
    if(bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now=GetWorld()->GetTimeSeconds(); if(Started<0) Started=Now;
    if(Now-Started>60) { Finish(false,TEXT("Population streaming or animation timed out")); return; }
    if(!bInitialized)
    {
        FString Json; TSharedPtr<FJsonObject> Source;
        if(!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectDir()/TEXT("../../shared/data/importedPopulation.json")))
            || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Source))
        { Finish(false,TEXT("Population ledger unavailable")); return; }
        TMap<FString,FName> Profiles;
        for(const auto& Value:Source->GetArrayField(TEXT("models")))
        { const auto Row=Value->AsObject(); Profiles.Add(Row->GetStringField(TEXT("key")),FName(*Row->GetStringField(TEXT("profile")))); }
        const auto Add=[&](const TSharedPtr<FJsonObject>& Row) {
            FExpected Entry; Entry.Id=FName(*Row->GetStringField(TEXT("id")));
            Entry.Zone=FName(*Row->GetStringField(TEXT("zone"))); Entry.Profile=Profiles.FindChecked(Row->GetStringField(TEXT("model")));
            Entry.Role=FName(*Row->GetStringField(TEXT("role"))); Entry.Name=Row->GetStringField(TEXT("name"));
            Expected.Add(Entry); Zones.AddUnique(Entry.Zone);
        };
        for(const auto& Value:Source->GetArrayField(TEXT("capitalAdditions")))
            if(Value->AsObject()->GetStringField(TEXT("zone"))==TEXT("riftspire_capital")) Add(Value->AsObject());
        for(const auto& Camp:Source->GetArrayField(TEXT("camps")))
            for(const auto& Value:Camp->AsObject()->GetArrayField(TEXT("members"))) Add(Value->AsObject());
        bInitialized=true;
    }
    auto* PC=Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Pawn=PC?Cast<AWarCharacter>(PC->GetPawn()):nullptr;
    auto* State=PC?PC->GetPlayerState<AWarPlayerState>():nullptr;
    auto* Streaming=GetWorld()->GetSubsystem<UWarZoneStreamingSubsystem>();
    if(!Pawn || !State || !Pawn->IsVisualReady() || !Streaming) return;
    FString Error; const FName Zone=Zones[ZoneIndex];
    if(!bQueued)
    {
        if(!Streaming->QueueGmZone(PC,Zone,Error)) { Finish(false,Error); return; }
        bQueued=true; return;
    }
    if(State->GetCurrentZone()!=Zone || !Streaming->IsZoneReady(Zone)) return;
    if(SampleTime<0)
    {
        for(TActorIterator<AWarCityNpc> It(GetWorld());It;++It)
            if(const auto* Idle=It->GetSkeletalMeshComponent()->GetSingleNodeInstance()) AnimationSamples.Add(It->NpcId,Idle->GetCurrentTime());
        SampleTime=Now; return;
    }
    if(Now-SampleTime<.65) return;
    for(const auto& Row:Expected)
    {
        if(Row.Zone!=Zone) continue;
        int32 Count=0;
        if(Row.Role==TEXT("enemy"))
        {
            for(TActorIterator<AWarEnemy> It(GetWorld());It;++It) if(It->ZoneId==Zone && It->EnemyId==Row.Id)
            {
                ++Count;
                if(!It->IsContentReady() || It->IsHidden() || It->GetDefinition().Profile!=Row.Profile || It->IsDead())
                { Finish(false,TEXT("Hostile identity or visual failed: ")+Row.Id.ToString()); return; }
            }
        }
        else
        {
            for(TActorIterator<AWarCityNpc> It(GetWorld());It;++It) if(It->NpcId==Row.Id)
            {
                ++Count; const auto* Mesh=It->GetSkeletalMeshComponent(); const auto* Idle=Mesh->GetSingleNodeInstance();
                const float* Earlier=AnimationSamples.Find(Row.Id);
                if(It->CharacterProfile!=Row.Profile || It->DisplayName!=Row.Name || It->CityRole!=Row.Role
                    || !It->IsEquipmentReady() || !Mesh->GetSkeletalMeshAsset() || !Mesh->IsVisible() || It->IsHidden()
                    || !Idle || !Earlier || FMath::IsNearlyEqual(*Earlier,Idle->GetCurrentTime()))
                { Finish(false,TEXT("Friendly identity, equipment or advancing idle failed: ")+Row.Id.ToString()); return; }
                // Ambient appearances must not invent services or become combat targets.
                if(!Pawn->TeleportTo(It->GetActorLocation()+FVector(180,0,100),FRotator::ZeroRotator))
                { Finish(false,TEXT("Inhabitant approach obstructed: ")+Row.Id.ToString()); return; }
                if(!It->GetService().IsNone() || It->CanInteract(Pawn) || Pawn->CanStrikeTarget(*It))
                { Finish(false,TEXT("Ambient service/combat boundary changed: ")+Row.Id.ToString()); return; }
            }
        }
        if(Count!=1) { Finish(false,TEXT("Missing or duplicate imported actor: ")+Row.Id.ToString()); return; }
        ++Checked;
    }
    ++ZoneIndex; bQueued=false; SampleTime=-1; Started=Now; AnimationSamples.Reset();
    if(ZoneIndex==Zones.Num()) Finish(Checked==21,TEXT("Eight Riftspire inhabitants, six friendly camp NPCs and seven hostile catalog identities verified in streamed runtime zones."));
}
