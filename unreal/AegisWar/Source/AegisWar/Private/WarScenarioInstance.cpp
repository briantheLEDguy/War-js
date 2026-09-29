#include "WarScenarioInstance.h"
#include "WarScenarioTransport.h"
#include "WarPlayerController.h"
#include "WarSiegeGameMode.h"
#include "WarPlayerState.h"
#include "GameFramework/GameSession.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void UWarScenarioInstance::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);FString File;
    if (!UE_BUILD_SHIPPING && IsRunningDedicatedServer() && FParse::Value(FCommandLine::Get(),TEXT("WarScenarioInstance="),File))
    {
        Config=WarScenarioTransport::ReadConfig(File);
        FString Key,Match,Url;
        if (!Config || !Config->TryGetStringField(TEXT("key"),Key) || Key.Len()<32 || !Config->TryGetStringField(TEXT("match"),Match)
            || !Config->TryGetStringField(TEXT("url"),Url) || !Url.StartsWith(TEXT("http://127.0.0.1:")))
        { Config.Reset();UE_LOG(LogTemp,Error,TEXT("WAR_SIEGE_CONTENT_BLOCKED invalid instance allocation")); }
    }
}
TStatId UWarScenarioInstance::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarScenarioInstance,STATGROUP_Tickables); }
bool UWarScenarioInstance::AllowsLan() const { bool Value=false;return Config && Config->TryGetBoolField(TEXT("allowLan"),Value) && Value; }
void UWarScenarioInstance::Send(const FString& Path,TSharedPtr<FJsonObject> Body,TFunction<void(bool,TSharedPtr<FJsonObject>,FString)> Reply)
{
    if (!Config) { Reply(false,nullptr,TEXT("Instance is not allocated."));return; }
    Body->SetStringField(TEXT("match"),Config->GetStringField(TEXT("match")));
    WarScenarioTransport::Request(Config->GetStringField(TEXT("url")),Config->GetStringField(TEXT("key")),TEXT("POST"),Path,Body,MoveTemp(Reply));
}
void UWarScenarioInstance::Admit(const FString& Ticket,TFunction<void(FString)> Complete)
{
    if (Ticket.Len()!=64 || InFlight.Contains(Ticket) || Pending.Contains(Ticket)) { Complete(TEXT("Missing or duplicate scenario admission ticket."));return; }
    InFlight.Add(Ticket);auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("ticket"),Ticket);
    const TWeakObjectPtr<UWarScenarioInstance> Weak=this;
    Send(TEXT("/instance/consume"),Body,[Weak,Ticket,Complete=MoveTemp(Complete)](bool Ok,TSharedPtr<FJsonObject> Data,FString Error) mutable {
        if (auto* Self=Weak.Get()) {
            Self->InFlight.Remove(Ticket);
            if (Ok) { Self->Pending.Add(Ticket,Data);Self->PendingAt.Add(Ticket,FPlatformTime::Seconds()); }
            Complete(Ok ? FString() : Error);
        } else Complete(TEXT("Scenario instance closed."));
    });
}
bool UWarScenarioInstance::Attach(AWarPlayerController* PC,const FString& Ticket,FString& Error)
{
    auto* Data=Pending.Find(Ticket);
    if (!Data || !WarScenarioTransport::Restore(PC,*Data,true,Error)) { Error=TEXT("Scenario character could not be restored: ")+Error;return false; }
    const FString Id=(*Data)->GetStringField(TEXT("id"));
    for (const auto& Pair:Players) if (Pair.Key.IsValid() && Pair.Value==Id) { Error=TEXT("Character already has a scenario connection.");return false; }
    Players.Add(PC,Id);Pending.Remove(Ticket);PendingAt.Remove(Ticket);
    if (FirstPlayerAt==0) FirstPlayerAt=FPlatformTime::Seconds();
    return true;
}
void UWarScenarioInstance::Disconnect(AWarPlayerController* PC)
{
    FString Id;if (!Players.RemoveAndCopyValue(PC,Id)) return;
    auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("id"),Id);
    Send(TEXT("/instance/disconnect"),Body,[](bool,TSharedPtr<FJsonObject>,FString){});
}
bool UWarScenarioInstance::CanStart(int32 Humans) const
{
    if (Humans<1 || !Roster) return false;
    for (const auto& Value:Roster->GetArrayField(TEXT("members")))
        if (Value->AsObject()->GetStringField(TEXT("phase"))==TEXT("travel") && FPlatformTime::Seconds()-FirstPlayerAt<120) return false;
    return true;
}
void UWarScenarioInstance::Finish()
{
    if (bFinished || !Config) return;bFinished=true;
    for (const auto& Pair:Players) if (auto* PC=Pair.Key.Get())
        if (APawn* Pawn=PC->GetPawn()) { PC->UnPossess();Pawn->Destroy(); }
    Send(TEXT("/instance/finish"),MakeShared<FJsonObject>(),[](bool,TSharedPtr<FJsonObject>,FString){});
}
void UWarScenarioInstance::Tick(float Delta)
{
    if (LastHeartbeat==0) LastHeartbeat=FPlatformTime::Seconds();
    if (Config && !bFinished && FPlatformTime::Seconds()-LastHeartbeat>15)
    {
        Finish();FPlatformMisc::RequestExit(false);return;
    }
    if (!Config || bPolling || FPlatformTime::Seconds()<NextPoll) return;
    NextPoll=FPlatformTime::Seconds()+1;bPolling=true;
    TArray<FString> Expired;
    for (const auto& Pair:PendingAt) if (FPlatformTime::Seconds()-Pair.Value>15) Expired.Add(Pair.Key);
    for (const auto& Ticket:Expired)
    {
        auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("id"),Pending[Ticket]->GetStringField(TEXT("id")));
        Send(TEXT("/instance/disconnect"),Body,[](bool,TSharedPtr<FJsonObject>,FString){});Pending.Remove(Ticket);PendingAt.Remove(Ticket);
    }
    const TWeakObjectPtr<UWarScenarioInstance> Weak=this;
    Send(TEXT("/instance/roster"),MakeShared<FJsonObject>(),[Weak](bool Ok,TSharedPtr<FJsonObject> Data,FString) {
        auto* Self=Weak.Get();if (!Self) return;Self->bPolling=false;if (!Ok) return;Self->Roster=Data;Self->LastHeartbeat=FPlatformTime::Seconds();
        if (Data->GetStringField(TEXT("phase"))==TEXT("finished")) { Self->Finish();FPlatformMisc::RequestExit(false);return; }
        TArray<AWarPlayerController*> Released;
        for (const auto& Value:Data->GetArrayField(TEXT("members")))
        {
            const auto Member=Value->AsObject();if (Member->GetStringField(TEXT("phase"))!=TEXT("return")) continue;
            const FString Id=Member->GetStringField(TEXT("id"));bool bOwned=false;
            for (const auto& Pair:Self->Players) if (Pair.Key.IsValid() && Pair.Value==Member->GetStringField(TEXT("id")))
            {
                auto* PC=Pair.Key.Get();if (APawn* Pawn=PC->GetPawn()) { PC->UnPossess();Pawn->Destroy(); }
                Released.AddUnique(PC);bOwned=true;
            }
            bool bAdmissionPending=!Self->InFlight.IsEmpty();
            for (const auto& Pair:Self->Pending) bAdmissionPending |= Pair.Value->GetStringField(TEXT("id"))==Id;
            // A lost admission response may consume the ticket without creating a pawn.
            // Confirm that absence too, so campaign recovery cannot wait forever.
            if (!bOwned && !bAdmissionPending) {
                auto Body=MakeShared<FJsonObject>();Body->SetStringField(TEXT("id"),Id);
                Self->Send(TEXT("/instance/disconnect"),Body,[](bool,TSharedPtr<FJsonObject>,FString){});
            }
        }
        for (auto* PC:Released) Self->Disconnect(PC);
    });
}
