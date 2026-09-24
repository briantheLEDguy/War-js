#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarAbilityWorkshopCombatProof.generated.h"
class FJsonObject;

/** Explicit loopback acceptance fixture; never enables GM privileges or production admission. */
UCLASS()
class AEGISWAR_API UWarAbilityWorkshopCombatProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type==EWorldType::Game; }
    virtual void Tick(float Delta) override;
    virtual TStatId GetStatId() const override;
private:
    int32 Step=0;
    double Next=0,Deadline=0;
    bool bFinished=false;
    TSharedPtr<FJsonObject> Workspace;
    TArray<FString> Checks;
    void Finish(bool Passed,const FString& Error);
    bool Check(bool Passed,const FString& Label);
    bool Stage(int32 Version,float Heal,float Tick,float Percent);
};
