#pragma once
#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Views/SListView.h"
#include "WarAbilityWorkshopDocument.h"

class AWarPlayerController;
class UWarAbilityWorkshopSubsystem;
class SVerticalBox;
class SHorizontalBox;
class SEditableTextBox;
class SScrollBar;
struct FWarWorkshopRow
{
    FString Id,AssignmentId,AbilityId,ClassName,EffectId,RuleId;
    TSharedPtr<FJsonObject> Ability,Assignment;
    int32 Depth=0;
};
struct FWarWorkshopColumn
{
    FString Id,Label;
    float Width=140;
    bool bNumber=false;
};

/** Virtualized native spreadsheet. Structural edits remain in the inspector until validated atomically. */
class SWarAbilityWorkshop : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SWarAbilityWorkshop) {} SLATE_END_ARGS()
    void Construct(const FArguments&,AWarPlayerController* InOwner);
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnKeyDown(const FGeometry&,const FKeyEvent&) override;
    virtual FReply OnMouseButtonDoubleClick(const FGeometry&,const FPointerEvent&) override;
    virtual void Tick(const FGeometry&,double,float) override;
    bool VerifyInteractions(FString& Error);
    bool VerifyAnalysis(FString& Error);
    bool VerifyReview(FString& Error);
private:
    TWeakObjectPtr<AWarPlayerController> Owner;
    TWeakObjectPtr<UWarAbilityWorkshopSubsystem> Store;
    TSharedPtr<SVerticalBox> Root,Grid,Inspector,ClassBrowser,SpecialPage;
    TSharedPtr<SHorizontalBox> Chips;
    TSharedPtr<SListView<TSharedPtr<FWarWorkshopRow>>> List;
    TSharedPtr<SEditableTextBox> CellEditor;
    TSharedPtr<SScrollBar> HorizontalScroll;
    TArray<TSharedPtr<FWarWorkshopRow>> Rows;
    TArray<FWarWorkshopColumn> Columns;
    TMap<FString,FString> Filters;
    TSet<FString> Classes,Expanded;
    FString Tab=TEXT("Class Abilities"),Preset=TEXT("Overview"),Query,SortColumn=TEXT("class"),SelectedAbility,SelectedAssignment;
    FString ViewName=TEXT("My view"),Notice,EditValue,BulkOperation=TEXT("set"),Section=TEXT("Basics"),PickerQuery;
    TSharedPtr<FJsonObject> Composer;
    TArray<FWarWorkshopCellEdit> PendingEdits;
    TSet<FString> PendingSelection;
    int32 AnchorRow=0,AnchorCol=0,FocusRow=0,FocusCol=0;
    float ScrollOffset=0,ViewportWidth=1920;
    bool bDescending=false,bCompact=false,bMaximized=true,bClasses=true,bInspector=false,bDirtyComposer=false,bEditingCell=false;
    uint64 ObservedSerial=0;
    uint64 ObservedRemoteSerial=0;
    double LastEditTime=0;
    TSharedPtr<FJsonObject> Scenario;
    FString Analysis;
    uint64 AnalysisDraft=MAX_uint64,ScenarioSerial=0,AnalysisScenario=MAX_uint64;
    int32 ReviewPage=0;

    // Slate font sizes are points at 96 DPI: 12 pt = 16 px; 10.5 pt = 14 px.
    float FontSize() const { return bCompact ? 10.5f : 12.f; }
    TSharedRef<SWidget> Label(const FString&,bool bMuted=false) const;
    TSharedRef<SWidget> Button(const FString&,TFunction<void()>);
    TSharedRef<SWidget> Choice(const FString&,const TArray<TPair<FString,FString>>&,TFunction<void(FString)>);
    TSharedRef<SWidget> Field(const FString&,const FString&,TFunction<void(FString)>);
    TSharedRef<SWidget> NumericField(const FString&,double,TFunction<void(double)>);
    TSharedRef<SWidget> AbilityPicker(const FString&,TFunction<void(FString)>);
    TSharedRef<SWidget> EffectPicker(const FString&,const FString&,TFunction<void(FString)>);
    void Build();
    void BuildGrid();
    void BuildClasses();
    void SetPreset(const FString&);
    void Refresh();
    void RefreshChips();
    void BuildInspector();
    void BuildSpecialPage();
    void BuildReview();
    void BuildScenario();
    void PreviewScenario();
    TSharedRef<ITableRow> GenerateRow(TSharedPtr<FWarWorkshopRow>,const TSharedRef<STableViewBase>&);
    TSharedRef<SWidget> Cells(const TSharedPtr<FWarWorkshopRow>&,bool bFrozen);
    TSharedRef<SWidget> Header(bool bFrozen);
    TSharedRef<SWidget> FilterMenu(const FWarWorkshopColumn&);
    FString Cell(const FWarWorkshopRow&,const FString&) const;
    FString Path(const FWarWorkshopRow&,const FString&) const;
    bool Matches(const FWarWorkshopRow&) const;
    void Select(int32,int32,bool);
    void EditCell();
    void CommitCell();
    void PrepareEdits(const FString&,const FString&);
    void CommitEdits();
    void Copy();
    void Paste();
    void FillDown();
    void SaveView(bool bLoad);
    void Changed();
    void SetComposer(const FString&,const FString&);
    void ApplyComposer();
    void NewAbility(bool bDuplicate);
    void AssignToClass(const FString&);
    void BuildEffect(const TSharedRef<SVerticalBox>&,const TSharedPtr<FJsonObject>&,bool bBonus=false);
    void BuildRule(const TSharedRef<SVerticalBox>&,const TSharedPtr<FJsonObject>&);
    void BuildCondition(const TSharedRef<SVerticalBox>&,const TSharedPtr<FJsonObject>&,const FString&,int32);
    TSharedPtr<FJsonObject> DefaultEffect(const FString&) const;
    void MarkComposer(bool bRebuild=false);
};
