#include "WarScenarioMenuProof.h"
#include "WarScenarioSession.h"
#include "WarFrontendWidget.h"
#include "WarRuntimeSettings.h"
#include "WarCharacterVisualDefinition.h"
#include "WarSiegeEquipment.h"
#include "EngineUtils.h"
#include "JsonObjectConverter.h"
#include "WarSiegeLobbyWidget.h"
#include "WarInterfaceWidget.h"
#include "WarSiegeGameMode.h"
#include "WarSiegeHud.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UObjectIterator.h"

namespace
{
    FString Folder()
    {
        FString Run; FGuid Guid; FParse::Value(FCommandLine::Get(),TEXT("WarScenarioMenuRun="),Run);
        return FGuid::Parse(Run,Guid) ? FPaths::ProjectSavedDir()/TEXT("ScenarioMenuProof")/Guid.ToString(EGuidFormats::Digits) : FString();
    }
    template<class T> T* Widget(UWorld* World)
    { for (TObjectIterator<T> It;It;++It) if (It->GetWorld()==World && It->IsInViewport()) return *It; return nullptr; }
    bool HasText(const TSharedRef<SWidget>& Item,const FString& Label)
    {
        if (Item->GetTypeAsString()==TEXT("STextBlock") && StaticCastSharedRef<STextBlock>(Item)->GetText().ToString()==Label) return true;
        auto* Children=Item->GetChildren();
        for (int32 I=0;Children && I<Children->Num();++I) if (HasText(Children->GetChildAt(I),Label)) return true;
        return false;
    }
    TSharedPtr<SButton> FindButton(const TSharedRef<SWidget>& Item,const FString& Label)
    {
        if (Item->GetTypeAsString()==TEXT("SButton") && HasText(Item,Label)) return StaticCastSharedRef<SButton>(Item);
        auto* Children=Item->GetChildren();
        for (int32 I=0;Children && I<Children->Num();++I) if (auto Button=FindButton(Children->GetChildAt(I),Label)) return Button;
        return nullptr;
    }
    bool Click(UUserWidget* Widget,const FString& Label)
    {
        const auto Button=Widget ? FindButton(Widget->TakeWidget(),Label) : nullptr;
        if (!Button || !Button->IsEnabled()) return false;
        Button->SimulateClick(); return true;
    }
}
bool UWarScenarioMenuProof::ShouldCreateSubsystem(UObject* Outer) const
{ return !UE_BUILD_SHIPPING && Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(),TEXT("WarScenarioMenuProof")) && !Folder().IsEmpty(); }
TStatId UWarScenarioMenuProof::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarScenarioMenuProof,STATGROUP_Tickables); }
void UWarScenarioMenuProof::Capture(const FString& Name)
{
    IFileManager::Get().MakeDirectory(*Folder(),true);
    FScreenshotRequest::RequestScreenshot(Folder()/(Name+TEXT(".png")),true,false);
}
void UWarScenarioMenuProof::Finish(bool Passed,const FString& Detail)
{
    Finished=true;
    auto Report=MakeShared<FJsonObject>(); Report->SetBoolField(TEXT("passed"),Passed);
    Report->SetStringField(TEXT("detail"),Detail); Report->SetBoolField(TEXT("releaseApproved"),false);
    FString Json; FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    IFileManager::Get().MakeDirectory(*Folder(),true);
    FFileHelper::SaveStringToFile(Json,*(Folder()/TEXT("report.json")));
    FPlatformMisc::RequestExitWithStatus(false,Passed ? 0 : 1);
}
void UWarScenarioMenuProof::Tick(float Delta)
{
    const double Now=FPlatformTime::Seconds();
    if (!Started) { Started=Now;Next=Now+5;FString Realm;FParse::Value(FCommandLine::Get(),TEXT("WarScenarioProofRealm="),Realm);Side=Realm==TEXT("riftbound") ? 1 : 0;FParse::Value(FCommandLine::Get(),TEXT("WarScenarioProofParty="),PartyRole); }
    if (Now-Started>600) { Finish(false,FString::Printf(TEXT("In-game queue proof timed out at step %d: %s"),Step,*GetGameInstance()->GetSubsystem<UWarScenarioSession>()->GetStatus()));return; }
    auto* World=GetWorld();if (!World) return;
    auto* PC=Cast<AWarPlayerController>(World->GetFirstPlayerController());
    auto* Pawn=PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    auto* GS=World->GetGameState<AWarSiegeGameState>();
    if ((Step==9 || Step==11) && Pawn && GS && Now<Next)
        Pawn->AddMovementInput((GS->ObjectiveLocation-Pawn->GetActorLocation()).GetSafeNormal2D());
    if (Now<Next) return;
    const auto* PS=PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
    auto* Frontend=Widget<UWarFrontendWidget>(World);
    auto* Panel=Widget<UWarInterfaceWidget>(World);
    auto* Session=GetGameInstance()->GetSubsystem<UWarScenarioSession>();
    const auto Inventory=[&]() { FString Text;if (PS) FJsonObjectConverter::UStructToJsonObjectString(PS->GetInventory(),Text);return Text; };
    const auto SaveBots=[&]() {
        BotPositions.Reset();for (TActorIterator<AWarSiegeCharacter> It(World);It;++It)
            if (*It!=Pawn && It->Unit==EWarSiegeUnit::Participant && It->GetPlayerState<AWarPlayerState>()
                && It->GetPlayerState<AWarPlayerState>()->GetRealm()==PS->GetRealm()) BotPositions.Add(*It,It->GetActorLocation());
    };
    if (Step>=8 && Step<=12 && (!Pawn || !PS || !GS)) return;
    if (Step==0)
    {
        if (!Frontend || !PC) return;
        if (FindButton(Frontend->TakeWidget(),TEXT("Scenario"))) { Finish(false,TEXT("Scenario remains on login screen"));return; }
        Capture(TEXT("login"));
        const auto* Settings=GetDefault<UWarRuntimeSettings>();
        auto* Visual=(Side==0 ? Settings->AegisDevelopmentVisual : Settings->RiftboundDevelopmentVisual).LoadSynchronous();
        if (!Visual) { Finish(false,TEXT("Current character visual unavailable"));return; }
        PC->ServerCreateDevelopmentCharacter(PartyRole.IsEmpty() ? TEXT("Scenario Queue Test") : PartyRole==TEXT("leader") ? TEXT("Scenario Party Lead") : TEXT("Scenario Party Member"),Visual->RaceId,Visual->ClassId,Visual->BodyVariant);
        ++Step;Next=Now+2;
    }
    else if (Step==1)
    {
        if (!Pawn || !Pawn->IsVisualReady() || !PS) return;
        if (PS->GetRealm()!=(Side==0 ? EWarRealm::Aegis : EWarRealm::Riftbound)) { Finish(false,TEXT("Wrong campaign realm"));return; }
        CampaignPosition=Pawn->GetActorLocation();CampaignInventory=Inventory();Capture(TEXT("capital"));
        PC->ShowInterface(TEXT("Menu"));++Step;Next=Now+1;
    }
    else if (Step==2) { if (!Click(Panel,TEXT("Scenario"))) return;++Step;Next=Now+2; }
    else if (Step==3)
    {
        if (FParse::Param(FCommandLine::Get(),TEXT("WarScenarioProofConnectionRetry")))
        {
            if (!Panel) { Finish(false,TEXT("Scenario panel disappeared during connection retry"));return; }
            const FString Status=Session->GetStatus();
            if (ConnectionStep==0 || ConnectionStep==2)
            {
                const FString Expected=ConnectionStep==0 ? TEXT("Scenario host is not configured.") : TEXT("Scenario host unavailable.");
                if (Session->IsConnecting()) return;
                if (!Status.StartsWith(Expected))
                { Finish(false,TEXT("Connection failure or retry action was not visible in Scenario: ")+Status);return; }
                // HTTP completion can precede the widget's layout tick in this frame.
                if (!HasText(Panel->TakeWidget(),Status) || !FindButton(Panel->TakeWidget(),TEXT("Connect / retry"))) return;
                if (!Pawn || Inventory()!=CampaignInventory) { Finish(false,TEXT("Failed connection changed the campaign character"));return; }
                Capture(ConnectionStep==0 ? TEXT("host-missing") : TEXT("host-unavailable"));
                ++ConnectionStep;Next=Now+1;return;
            }
            if (ConnectionStep==1 || ConnectionStep==3)
            {
                if (!FPaths::FileExists(Folder()/(ConnectionStep==1 ? TEXT("retry-offline") : TEXT("retry-ready")))) return;
                if (!Click(Panel,TEXT("Connect / retry"))) return;
                if (!Session->IsConnecting() || Session->GetStatus()!=TEXT("Connecting to scenario host..."))
                { Finish(false,TEXT("Retry did not show immediate connection progress"));return; }
                // Repeated clicks during HTTP registration must not issue another registration.
                Session->Connect(PC);
                ++ConnectionStep;Next=Now+1;return;
            }
            if (!Session->GetView() || Session->GetPhase()!=TEXT("idle")) return;
            if (ConnectionStep==4)
            {
                if (Session->IsConnecting() || !FindButton(Panel->TakeWidget(),TEXT("Ready")) || Inventory()!=CampaignInventory)
                { Finish(false,TEXT("Retry did not restore the ready/queue panel with the same character"));return; }
                Capture(TEXT("connected"));++ConnectionStep;Next=Now+2;return;
            }
            Finish(true,TEXT("Missing and stopped host errors are visible; Connect / retry restores the queue panel."));return;
        }
        if (!Session->GetView() || Session->GetPhase()!=TEXT("idle")) return;
        if (!PartyRole.IsEmpty() && Session->GetView()->GetObjectField(TEXT("party"))->GetArrayField(TEXT("members")).Num()<2)
        {
            if (PartyRole==TEXT("leader") && !PartyInvited) PartyInvited=Click(Panel,TEXT("Invite Scenario Party Member"));
            if (PartyRole==TEXT("member")) Click(Panel,TEXT("Accept invitation from Scenario Party Lead"));
            return;
        }
        if (!Click(Panel,TEXT("Ready"))) return;++Step;Next=Now+2;
    }
    else if (Step==4)
    {
        if (PartyRole==TEXT("member")) { if (Session->GetPhase()!=TEXT("queued")) return; }
        else {
            if (!PartyRole.IsEmpty()) for (const auto& Member:Session->GetView()->GetObjectField(TEXT("party"))->GetArrayField(TEXT("members"))) if (!Member->AsObject()->GetBoolField(TEXT("ready"))) return;
            if (!Click(Panel,TEXT("Queue for Breach the Lower City"))) return;
        }
        ++Step;Next=Now+2;
    }
    else if (Step==5) { Capture(TEXT("queue"));++Step;Next=Now+1; }
    else if (Step==6)
    {
        if (Session->GetPhase()!=TEXT("offered") || !Click(Panel,TEXT("Accept match"))) return;
        Capture(TEXT("offer"));++Step;Next=Now+2;
    }
    else if (Step==7)
    {
        if (!GS || GS->Siege.Phase!=EWarSiegePhase::Active || !Pawn || !Pawn->IsVisualReady() || !PS) return;
        if (!GS->bQueuedScenario || GS->Siege.Capacity!=6 || Inventory()!=CampaignInventory) { Finish(false,TEXT("Character transfer or match configuration changed"));return; }
        int32 Engines=0,Engineers=0;
        for (TActorIterator<AWarSiegeEquipment> It(World);It;++It) { ++Engines;for (const auto& Crew:It->Engineers) Engineers+=IsValid(Crew) && Crew->IsVisualReady(); }
        if (Engines!=2 || Engineers!=4) return;
        if (GS->Siege.Objective!=0) { Finish(false,TEXT("Equipment did not appear before supplies capture"));return; }
        Capture(TEXT("combat"));PC->CloseInterface();PC->ServerSiegeSquadOrder(GS->RoundId,0);++Step;Next=Now+3;
    }
    else if (Step==8) { BeforeMove=Pawn->GetActorLocation();SaveBots();++Step;Next=Now+4; }
    else if (Step==9) { ++Step;Next=Now+3; }
    else if (Step==10)
    {
        bool Followed=false;for (const auto& Pair:BotPositions) if (Pair.Key.IsValid() && FVector::Dist2D(Pair.Key->GetActorLocation(),Pair.Value)>100) Followed=true;
        if (PC->SiegeSquadCount<1 || FVector::Dist2D(Pawn->GetActorLocation(),BeforeMove)<100 || !Followed) { Finish(false,TEXT("Player-led squad failed to move from staging"));return; }
        PC->ServerSiegeSquadOrder(GS->RoundId,2);OrderAnchor=Pawn->GetActorLocation();++Step;Next=Now+5;
    }
    else if (Step==11)
    {
        if (PC->SiegeSquadOrder!=2) { Finish(false,TEXT("Hold order was not acknowledged at a validated anchor"));return; }
        Capture(TEXT("hold"));
        if (PartyRole!=TEXT("member")) PC->ServerSiegeSquadOrder(GS->RoundId,1);
        ++Step;Next=Now+4;
    }
    else if (Step==12)
    {
        if (PC->SiegeSquadOrder!=(PartyRole==TEXT("member") ? 2 : 1)) { Finish(false,TEXT("Squad order was not acknowledged or another player changed it"));return; }
        if (!OptionalChecked && PartyRole!=TEXT("member") && !GS->Siege.bOptionalComplete)
        {
            if (auto* Hud=PC->GetHUD<AWarSiegeHud>()) Hud->NotifyHitBoxClick(TEXT("Squad3"));
            Step=18;Next=Now+2;return;
        }
        if (FParse::Param(FCommandLine::Get(),TEXT("WarScenarioProofReconnect")))
        {
            Capture(TEXT("before-disconnect"));Step=16;Next=Now+24;
            GEngine->HandleDisconnect(World,World->GetNetDriver());return;
        }
        if (FParse::Param(FCommandLine::Get(),TEXT("WarScenarioProofRecovery")))
        { Capture(TEXT("await-recovery"));Step=14;Next=Now+2;return; }
        int32 HoldSeconds=2;FParse::Value(FCommandLine::Get(),TEXT("WarScenarioProofHold="),HoldSeconds);
        PC->ShowInterface(TEXT("Scenario"));++Step;Next=Now+FMath::Clamp(HoldSeconds,2,180);
    }
    else if (Step==13) {
        if (!PC) return;
        if (!Panel) { PC->ShowInterface(TEXT("Scenario"));Next=Now+1;return; }
        if (!Click(Panel,TEXT("Leave scenario and return"))) return;++Step;Next=Now+3;
    }
    else if (Step==14)
    {
        if (World->GetNetMode()!=NM_Standalone || !Pawn || !Pawn->IsVisualReady() || Session->IsRunning()) return;
        if (Inventory()!=CampaignInventory || PS->GetRealm()!=(Side==0 ? EWarRealm::Aegis : EWarRealm::Riftbound)
            || PS->IsSiegeNormalized() || FVector::Dist(Pawn->GetActorLocation(),CampaignPosition)>150) { Finish(false,TEXT("Campaign state or return position was not restored"));return; }
        Capture(TEXT("returned"));++Step;Next=Now+2;
    }
    else if (Step==15) Finish(true,TEXT("Current character queued from the capital, accepted a separate 6v6 instance, saw the parked convoy and four engineers, moved with their squad, issued orders, and returned with campaign inventory and realm preserved."));
    else if (Step==16)
    {
        if (!PC || Session->GetPhase()!=TEXT("disconnected")) return;
        if (!Panel) { PC->ShowInterface(TEXT("Scenario"));return; }
        if (!Click(Panel,TEXT("Reconnect to match"))) return;
        Capture(TEXT("reconnect"));++Step;Next=Now+2;
    }
    else if (Step==17)
    {
        if (Session->GetPhase()!=TEXT("playing") || !Pawn || !PS || !GS || !Pawn->IsVisualReady() || PC->SiegeSquadCount<1) return;
        if (Inventory()!=CampaignInventory) { Finish(false,TEXT("Reconnect changed the current character"));return; }
        Capture(TEXT("reconnected"));PC->ShowInterface(TEXT("Scenario"));Step=13;Next=Now+3;
    }
    else if (Step==18)
    {
        if (!PC || !GS || !Pawn) return;
        if (PC->SiegeSquadOrder!=3) { Finish(false,TEXT("Optional objective HUD order was not acknowledged"));return; }
        Capture(TEXT("optional-order"));OptionalChecked=true;PC->ServerSiegeSquadOrder(GS->RoundId,1);Step=12;Next=Now+2;
    }
}
