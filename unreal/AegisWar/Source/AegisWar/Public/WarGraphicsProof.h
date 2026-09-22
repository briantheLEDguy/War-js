#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarGraphicsSettings.h"
#include "WarGraphicsProof.generated.h"

class UWarGraphicsWidget;
class UWarFrontendWidget;

/** Opt-in rendered transaction proof using a dedicated preferences file. */
UCLASS()
class AEGISWAR_API UWarGraphicsProof : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game; }
    virtual TStatId GetStatId() const override;
    virtual void Tick(float DeltaTime) override;
private:
    void Finish(bool bPassed, const FString& Detail);
    UPROPERTY() TObjectPtr<UWarGraphicsWidget> Page;
    UPROPERTY() TObjectPtr<UWarFrontendWidget> Entry;
    FWarGraphicsSnapshot Baseline;
    double NextStep = 0;
    double Started = 0;
    int32 Step = 0;
    bool bFinished = false;
};
