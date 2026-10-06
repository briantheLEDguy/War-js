#include "WarInterfaceWidget.h"
#include "WarScenarioSession.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarSiegeEncounter.h"
#include "Engine/GameInstance.h"
#include "Serialization/JsonSerializer.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"
void UWarInterfaceWidget::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);
    if (CurrentPage!=TEXT("Scenario") || !Body) return;
    const auto* Session=GetGameInstance()->GetSubsystem<UWarScenarioSession>();
    const auto View=Session->GetView();FString Text;
    if (View) FJsonSerializer::Serialize(View.ToSharedRef(),TJsonWriterFactory<>::Create(&Text));
    Text+=TEXT("\n")+Session->GetStatus();
    if (Text!=LastScenarioView) { LastScenarioView=Text;Refresh();ForceLayoutPrepass(); }
}
void UWarInterfaceWidget::ScenarioPage()
{
    auto* Session=GetGameInstance()->GetSubsystem<UWarScenarioSession>();
    Body->AddSlot().AutoHeight().Padding(0,0,0,14)[SNew(STextBlock).AutoWrapText(true)
        .Font(FCoreStyle::GetDefaultFontStyle("Regular",16))
        .Text_Lambda([Session] { return FText::FromString(Session->GetStatus()); })];
    if (auto* PC = Cast<AWarPlayerController>(GetOwningPlayer()))
    {
        const auto* PS = PC->GetPlayerState<AWarPlayerState>();
        if (PS && !PS->IsScenarioTransferPending())
        {
            const auto* Siege = PS->GetSiegeEncounter();
            if (Siege && Siege->bCampaign)
                AddButton(TEXT("Leave live capital siege"), [PC] { PC->ServerCampaignSiegeEnrollment(false); });
            else if (!PS->IsSiegeMember())
                AddButton(TEXT("Enroll in live capital siege (normal stats)"), [PC] { PC->ServerCampaignSiegeEnrollment(true); });
        }
    }
    const auto View=Session->GetView();
    if (!View)
    {
        AddText(TEXT("Enter a character and connect to the scenario host. Your realm and character carry into each match."));
        if (!Session->IsConnecting())
            AddButton(TEXT("Connect / retry"),[this,Session] { if (auto* PC=Cast<AWarPlayerController>(GetOwningPlayer())) Session->Connect(PC); });
    }
    else
    {
        const FString Phase=View->GetStringField(TEXT("phase")),Id=View->GetStringField(TEXT("id"));
        const auto Party=View->GetObjectField(TEXT("party"));const bool Leader=Party->GetStringField(TEXT("leader"))==Id;
        AddText(TEXT("Your party"),20);
        for (const auto& Value:Party->GetArrayField(TEXT("members")))
        {
            const auto Member=Value->AsObject();const FString MemberId=Member->GetStringField(TEXT("id"));
            AddText(Member->GetStringField(TEXT("name"))+(Member->GetBoolField(TEXT("ready")) ? TEXT(" — Ready") : TEXT(" — Not ready")));
            if (Phase==TEXT("idle") && Leader && MemberId!=Id)
            {
                AddButton(TEXT("Make leader: ")+Member->GetStringField(TEXT("name")),[Session,MemberId] { Session->Command(TEXT("leader"),MemberId); });
                AddButton(TEXT("Remove: ")+Member->GetStringField(TEXT("name")),[Session,MemberId] { Session->Command(TEXT("kick"),MemberId); });
            }
        }
        if (Phase==TEXT("idle"))
        {
            bool Ready=false;for (const auto& V:Party->GetArrayField(TEXT("members"))) if (V->AsObject()->GetStringField(TEXT("id"))==Id) Ready=V->AsObject()->GetBoolField(TEXT("ready"));
            AddButton(Ready ? TEXT("Not ready") : TEXT("Ready"),[Session,Ready] { Session->Command(Ready ? TEXT("unready") : TEXT("ready")); });
            for (const auto& Value:View->GetArrayField(TEXT("catalog")))
            {
                const auto Definition=Value->AsObject();const FString Scenario=Definition->GetStringField(TEXT("id"));
                const int32 Capacity=Definition->GetIntegerField(TEXT("capacity"));
                AddText(Definition->GetStringField(TEXT("name"))+FString::Printf(TEXT(" · %dv%d\n"),Capacity,Capacity)
                    +Definition->GetStringField(TEXT("description")));
                if (Leader) AddButton(TEXT("Queue for ")+Definition->GetStringField(TEXT("name")),[Session,Scenario] { Session->Command(TEXT("queue"),Scenario); });
            }
            AddButton(TEXT("Leave party"),[Session] { Session->Command(TEXT("leaveParty")); });
            for (const auto& Value:View->GetArrayField(TEXT("invites")))
            {
                const auto Invite=Value->AsObject();const FString PartyId=Invite->GetStringField(TEXT("id"));
                AddButton(TEXT("Accept invitation from ")+Invite->GetStringField(TEXT("name")),[Session,PartyId] { Session->Command(TEXT("acceptInvite"),PartyId); });
                AddButton(TEXT("Decline invitation"),[Session,PartyId] { Session->Command(TEXT("declineInvite"),PartyId); });
            }
            if (Leader) for (const auto& Value:View->GetArrayField(TEXT("availablePlayers")))
            {
                const auto Other=Value->AsObject();const FString OtherId=Other->GetStringField(TEXT("id"));
                AddButton(TEXT("Invite ")+Other->GetStringField(TEXT("name")),[Session,OtherId] { Session->Command(TEXT("invite"),OtherId); });
            }
        }
        else if (Phase==TEXT("queued")) AddButton(TEXT("Leave queue"),[Session] { Session->Cancel(); });
        else if (Phase==TEXT("offered"))
        {
            const bool Accepted=View->GetObjectField(TEXT("match"))->GetBoolField(TEXT("accepted"));
            AddText(Accepted ? TEXT("Accepted — waiting for the other players.") : TEXT("Match found. Accept within 30 seconds."));
            if (!Accepted) AddButton(TEXT("Accept match"),[Session] { Session->Command(TEXT("accept")); });
            AddButton(TEXT("Decline match"),[Session] { Session->Cancel(); });
        }
        else if (Phase==TEXT("disconnected"))
        {
            AddButton(TEXT("Reconnect to match"),[Session] { Session->Command(TEXT("reconnect")); });
            AddButton(TEXT("Return to campaign"),[Session] { Session->Leave(); });
        }
        else if (Phase==TEXT("playing") || Phase==TEXT("travel")) AddButton(TEXT("Leave scenario and return"),[Session] { Session->Leave(); });
        else AddText(Phase==TEXT("allocating") ? TEXT("Preparing your match instance…") : TEXT("Restoring your campaign character…"));
    }
    AddButton(TEXT("Back to game"),[this] { if (auto* PC=Cast<AWarPlayerController>(GetOwningPlayer())) PC->CloseInterface(); });
}
