#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "Dom/JsonObject.h"
#include "WarTypes.h"
#include "WarScenarioSession.generated.h"
class AWarPlayerController;
/** Client of the shared development scenario host; owns no match server process. */
UCLASS()
class AEGISWAR_API UWarScenarioSession : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    virtual void Tick(float Delta) override;
    virtual bool IsTickable() const override { return !IsTemplate() && !Token.IsEmpty(); }
    virtual TStatId GetStatId() const override;
    void Connect(AWarPlayerController* PC);
    void SetConnectionStatus(bool Pending,const FString& Message);
    bool IsConnecting() const { return bConnecting; }
    void RegisterAuthority(AWarPlayerController* PC,const FString& DepartureTicket=FString());
    void SetCredentials(const FString& Url,const FString& Credential,const FString& Id);
    void Command(const FString& Action,const FString& Target=FString());
    bool RestorePending(AWarPlayerController* PC);
    void CompleteReturn(AWarPlayerController* PC);
    void Travel(const FString& Endpoint,const FString& Ticket);
    void Cancel();
    void Leave();
    bool IsRunning() const { return bInScenario || Phase==TEXT("travel") || Phase==TEXT("return"); }
    const FString& GetStatus() const { return Status; }
    const FString& GetPhase() const { return Phase; }
    TSharedPtr<FJsonObject> GetView() const { return View; }
    // Legacy proof callers receive an explicit error; no login-side launch remains.
    bool Start(EWarRealm Realm);
    static bool CanStart(bool Shipping, ENetMode Mode, EWarRealm Realm);
private:
    void ApplyView(TSharedPtr<FJsonObject> Data);
    FString Url,Token,CharacterId,Status,Phase,ReturnTicket,ReturnMap;
    FVector ReturnPosition=FVector::ZeroVector;
    bool bPolling=false,bTravelPending=false,bReturnPending=false,bInScenario=false,bRestoreInFlight=false;
    bool bReturnPawnReady=false,bReturnAckInFlight=false;
    bool bConnecting=false;
    TSet<TWeakObjectPtr<AWarPlayerController>> PendingRegistrations;
    double NextPoll=0;
    TSharedPtr<FJsonObject> View;
    TSharedPtr<FJsonObject> ReturnRuntime;
    FDelegateHandle NetworkFailure,TravelFailure;
};
