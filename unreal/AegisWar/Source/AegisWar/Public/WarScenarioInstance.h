#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "Dom/JsonObject.h"
#include "WarScenarioInstance.generated.h"
class AWarPlayerController;
UCLASS()
class AEGISWAR_API UWarScenarioInstance : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Tick(float Delta) override;
    virtual bool IsTickable() const override { return !IsTemplate() && Config.IsValid(); }
    virtual TStatId GetStatId() const override;
    bool IsEnabled() const { return Config.IsValid(); }
    bool AllowsLan() const;
    bool Owns(AWarPlayerController* PC) const { return !IsEnabled() || (!bFinished && Players.Contains(PC)); }
    bool CanStart(int32 Humans) const;
    void Admit(const FString& Ticket,TFunction<void(FString)> Complete);
    bool Attach(AWarPlayerController* PC,const FString& Ticket,FString& Error);
    void Disconnect(AWarPlayerController* PC);
    void Finish();
private:
    void Send(const FString& Path,TSharedPtr<FJsonObject> Body,TFunction<void(bool,TSharedPtr<FJsonObject>,FString)> Reply);
    TSharedPtr<FJsonObject> Config;
    TMap<FString,TSharedPtr<FJsonObject>> Pending;
    TMap<FString,double> PendingAt;
    TSet<FString> InFlight;
    TMap<TWeakObjectPtr<AWarPlayerController>,FString> Players;
    TSharedPtr<FJsonObject> Roster;
    double NextPoll=0,FirstPlayerAt=0,LastHeartbeat=0;
    bool bPolling=false,bFinished=false;
};
